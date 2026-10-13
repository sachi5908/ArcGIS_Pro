# Paste this ENTIRE file into ArcGIS Pro > Analysis > Python Window.
# Open the map you want to receive the results BEFORE running. Save your work.
# Self-contained: no earlier watershed helper scripts are required.
# Processing runs in Pro's separate Python; results go into THIS active map.
# The Python window waits for completion (normally about 1-2 minutes).
# No new project is created and the open project is not automatically saved.
# Live map insertion can still encounter an ArcGIS native bug; GUI verification
# is required. Outputs and a ready-to-add .lyrx file survive such a failure.

WATERSHED_WORKER_SOURCE = r'''
import datetime as dt
import json
from pathlib import Path
import sys
import arcpy as ap
from arcpy.sa import (Con, Fill, FlowAccumulation, FlowDirection,
                      StreamLink, StreamOrder, StreamToFeature, Watershed)

def log(message):
    print(f'[{dt.datetime.now().isoformat(timespec="seconds")}] {message}', flush=True)

def raster(value, path):
    value.save(str(path))
    return str(path)

def process(config):
    run = Path(config['run_dir'])
    out = run / 'outputs'
    scratch = run / 'scratch'
    out.mkdir()
    scratch.mkdir()
    if not ap.Exists(config['input_dem']):
        raise FileNotFoundError(config['input_dem'])
    if ap.Describe(config['input_dem']).spatialReference.name == 'Unknown':
        raise ValueError('The DEM must have a known coordinate system.')
    if ap.CheckExtension('Spatial') != 'Available':
        raise RuntimeError('Spatial Analyst is unavailable.')
    if ap.ProductInfo() not in ('ArcInfo', 'ArcEditor'):
        raise RuntimeError('SmoothLine requires a Standard or Advanced license.')
    if ap.CheckOutExtension('Spatial') != 'CheckedOut':
        raise RuntimeError('Could not check out Spatial Analyst.')
    # Deliberately no CheckInExtension: that call crashes on this installation.
    # Esri returns the license when this SHORT-LIVED standalone worker ends.
    # Do not paste/run this worker directly in the long-lived Pro Python window.
    with ap.EnvManager(workspace=str(out), scratchWorkspace=str(scratch),
                       overwriteOutput=False, addOutputsToMap=False,
                       parallelProcessingFactor='50%', compression='LZW'):
        log('1/13 Projecting DEM to UTM 44N')
        projected = str(out / 'DEM_UTM44N.tif')
        ap.management.ProjectRaster(config['input_dem'], projected,
                                    ap.SpatialReference(32644), 'NEAREST')
        with ap.EnvManager(snapRaster=projected, cellSize=projected,
                           extent=projected, outputCoordinateSystem=ap.SpatialReference(32644)):
            log('2/13 Filling sinks')
            filled = raster(Fill(projected), scratch / 'Filled_DEM.tif')
            log('3/13 Flow Direction (D8)')
            direction = raster(FlowDirection(filled, force_flow='NORMAL',
                                             flow_direction_type='D8'),
                               scratch / 'Flow_Direction.tif')
            log('4/13 Flow Accumulation')
            accumulation = raster(FlowAccumulation(direction, data_type='FLOAT',
                                                   flow_direction_type='D8'),
                                  scratch / 'Flow_Accumulation.tif')
            maximum = float(ap.management.GetRasterProperties(accumulation, 'MAXIMUM')[0])
            if maximum <= config['threshold']:
                raise ValueError('Threshold is too high: no stream cells would be extracted.')
            log('5/13 Extracting stream network')
            streams = raster(Con(ap.Raster(accumulation) > config['threshold'], 1),
                             scratch / 'Streams.tif')
            log('6/13 Strahler stream order')
            order = raster(StreamOrder(streams, direction, 'STRAHLER'),
                           scratch / 'Stream_Order.tif')
            log('7/13 Converting streams to features')
            raw = str(out / 'Stream_Network_Raw.shp')
            StreamToFeature(order, direction, raw, 'NO_SIMPLIFY')
            log('8/13 Smoothing stream lines')
            smooth = str(out / 'Stream_Network_Smoothed.shp')
            ap.cartography.SmoothLine(raw, smooth, 'PAEK', config['smoothing'])
            log('9/13 Stream links')
            links = raster(StreamLink(streams, direction), scratch / 'Stream_Links.tif')
            log('10/13 Tributary sub-basins')
            sub_raster = raster(Watershed(direction, links), out / 'Sub_Basins_Ras.tif')
            sub_vector = str(out / 'Sub_Basins.shp')
            ap.conversion.RasterToPolygon(sub_raster, sub_vector, 'NO_SIMPLIFY', 'Value')
            log(f'11/13 Maximum-flow outlet: {maximum}')
            outlet = raster(Con(ap.Raster(accumulation) == maximum, 1), scratch / 'Pour_Point.tif')
            log('12/13 Main watershed')
            main_raster = raster(Watershed(direction, outlet), out / 'Main_Watershed.tif')
            main_vector = str(out / 'Main_Basin.shp')
            ap.conversion.RasterToPolygon(main_raster, main_vector, 'SIMPLIFY', 'Value')
            log('13/13 Clipping sub-basins and streams')
            ap.analysis.Clip(sub_vector, main_vector, str(out / 'Clipped_Sub_Basins.shp'))
            ap.analysis.Clip(smooth, main_vector, str(out / 'Clipped_Streams.shp'))
    counts = {name: int(ap.management.GetCount(str(out / name))[0]) for name in
              ('Main_Basin.shp', 'Clipped_Sub_Basins.shp', 'Clipped_Streams.shp')}
    if not all(counts.values()):
        raise RuntimeError(f'Unexpected empty output: {counts}')
    (run / 'processing.json').write_text(json.dumps(counts, indent=2), encoding='utf-8')
    log('Processing saved; worker exiting normally to release its license.')

def prepare_layers(config):
    run = Path(config['run_dir'])
    folder = run / 'layers'
    folder.mkdir()
    specifications = [
        ('Main_Watershed.tif', 'Main Watershed (Raster)', None, 50),
        ('Sub_Basins_Ras.tif', 'Sub-Basin Watersheds (Raster)', None, 40),
        ('Main_Basin.shp', 'Main Watershed Boundary', None, 0),
        ('Clipped_Sub_Basins.shp', 'Tributary Sub-Basins', 'gridcode', 40),
        ('Clipped_Streams.shp', 'Stream Network', 'grid_code', 0),
    ]
    bundle = None
    with ap.EnvManager(addOutputsToMap=False, overwriteOutput=False):
        for index, (name, title, field, transparency) in enumerate(specifications):
            log(f'Preparing saved layer: {title}')
            source = str(run / 'outputs' / name)
            temporary = f'watershed_layer_{index}'
            is_raster = name.endswith('.tif')
            make = ap.management.MakeRasterLayer if is_raster else ap.management.MakeFeatureLayer
            result = make(source, temporary)
            path = folder / (Path(name).stem + '.lyrx')
            ap.management.SaveToLayerFile(result.getOutput(0), str(path), 'ABSOLUTE')
            layer_file = ap.mp.LayerFile(str(path))
            layer = layer_file.listLayers()[0]
            layer.name = title
            layer.transparency = transparency
            if is_raster:
                layer.visible = config['show_rasters']
            else:
                sym = layer.symbology
                if field:
                    if field not in {f.name for f in ap.ListFields(source)}:
                        raise ValueError(f'Missing field {field} in {source}')
                    sym.updateRenderer('UniqueValueRenderer')
                    sym.renderer.fields = [field]
                else:
                    sym.updateRenderer('SimpleRenderer')
                    sym.renderer.symbol.color = {'RGB': [0, 0, 0, 0]}
                    sym.renderer.symbol.outlineColor = {'RGB': [0, 0, 0, 100]}
                    sym.renderer.symbol.outlineWidth = 1.5
                layer.symbology = sym
            layer_file.save()
            if bundle is None:
                bundle = layer_file
            else:
                bundle.addLayer(layer_file, 'TOP')
            ap.management.Delete(temporary)
        bundle_path = run / 'Watershed_Results.lyrx'
        bundle.saveACopy(str(bundle_path))
        check = ap.mp.LayerFile(str(bundle_path))
        if len(check.listLayers()) != 5 or check.listBrokenDataSources():
            raise RuntimeError('Saved layer collection is incomplete or has broken sources.')
    (run / 'layers.json').write_text(json.dumps({'layer_file': str(bundle_path)}, indent=2),
                                    encoding='utf-8')
    log('Five styled layers prepared without opening or creating a project.')

if __name__ == '__main__':
    config = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    log(f'ArcGIS Python: {sys.executable}')
    try:
        if sys.argv[1] == 'process':
            process(config)
        elif sys.argv[1] == 'layers':
            prepare_layers(config)
        else:
            raise ValueError('Unknown worker phase.')
    except Exception:
        import traceback
        traceback.print_exc()
        print(ap.GetMessages(2), flush=True)
        sys.exit(1)
'''


def watershed_in_current_project():
    import datetime as dt
    import json
    import math
    import os
    from pathlib import Path
    import subprocess
    import uuid
    import arcpy as ap

    # EDIT THESE SETTINGS IF NEEDED. UTM 44N is retained for this supplied DEM.
    input_dem = Path(r'C:\Users\sachi\OneDrive\Desktop\check\Test_Data\input\n24_e079_1arc_v3.tif')
    output_root = Path(r'C:\Users\sachi\OneDrive\Desktop\check\Test_Data\current_project_runs')
    threshold = 50000
    smoothing = '90 Meters'
    show_rasters = True
    propy = Path(r'C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat')

    # Capture the actual current project/map; no hardcoded APRX or project copy.
    project = ap.mp.ArcGISProject('CURRENT')
    target = project.activeMap
    if target is None:
        raise RuntimeError('Open the destination map tab, then paste/run this code again.')
    if target.mapType != 'MAP':
        raise RuntimeError('Open a 2D map, not a 3D scene, before running this workflow.')
    if not input_dem.is_file():
        raise FileNotFoundError(f'Input DEM not found: {input_dem}')
    if not propy.is_file():
        raise FileNotFoundError(f'ArcGIS Python launcher not found: {propy}')
    if not math.isfinite(float(threshold)) or threshold <= 0:
        raise ValueError('Threshold must be positive and finite.')

    run = output_root / (dt.datetime.now().strftime('%Y%m%d_%H%M%S')
                         + '_' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    worker = run / 'worker.py'
    worker.write_text(WATERSHED_WORKER_SOURCE, encoding='utf-8')
    config_path = run / 'job.json'
    config_path.write_text(json.dumps({
        'run_dir': str(run), 'input_dem': str(input_dem), 'threshold': threshold,
        'smoothing': smoothing, 'show_rasters': show_rasters,
        'current_project': project.filePath, 'current_map': target.name,
    }, indent=2), encoding='utf-8')
    status = {'state': 'running', 'project': project.filePath,
              'map': target.name, 'run_dir': str(run), 'phases': {}}

    def write_status():
        temporary = run / 'status.tmp'
        temporary.write_text(json.dumps(status, indent=2), encoding='utf-8')
        temporary.replace(run / 'status.json')

    environment = os.environ.copy()
    for key in ('PYTHONHOME', 'PYTHONPATH'):
        environment.pop(key, None)
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONUNBUFFERED'] = '1'
    command_shell = os.environ.get('COMSPEC', r'C:\Windows\System32\cmd.exe')
    write_status()
    print(f'Running watershed for CURRENT map: {target.name}', flush=True)
    print(f'Outputs and log: {run}', flush=True)
    print('Please wait. Processing is isolated; the Python window remains busy.', flush=True)
    try:
        with (run / 'run.log').open('w', encoding='utf-8', buffering=1) as log_file:
            for phase in ('process', 'layers'):
                status['phase'] = phase
                write_status()
                # Raw cmd command line avoids incorrect list2cmdline escaping
                # of the nested quotes around the installed propy.bat path.
                command = f'"{command_shell}" /d /s /c ""{propy}" -u "{worker}" {phase} "{config_path}""'
                with subprocess.Popen(command, cwd=str(run), env=environment,
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True,
                                      encoding='utf-8', errors='replace',
                                      creationflags=subprocess.CREATE_NO_WINDOW) as child:
                    for line in child.stdout:
                        log_file.write(line)
                        print(line.rstrip(), flush=True)
                    code = child.wait()
                status['phases'][phase] = {'exit_code': code,
                                           'exit_hex': f'0x{code & 0xffffffff:08X}'}
                if code != 0:
                    raise RuntimeError(f'{phase} worker failed (0x{code & 0xffffffff:08X}). '
                                       f'See {run / "run.log"}')
                manifest = run / ('processing.json' if phase == 'process' else 'layers.json')
                if not manifest.is_file():
                    raise RuntimeError(f'{phase} worker did not produce its completion manifest.')

            # Only now touch the live map, after both child processes exited.
            # Styles were saved OFFLINE; no live renderer/gallery updates.
            status['phase'] = 'adding_to_current_map'
            write_status()
            message = f'BEFORE adding prepared layers to CURRENT map: {target.name}'
            log_file.write(message + '\n')
            print(message, flush=True)
            layer_file = ap.mp.LayerFile(str(run / 'Watershed_Results.lyrx'))
            if len(layer_file.listLayers()) != 5 or layer_file.listBrokenDataSources():
                raise RuntimeError('Prepared layer file is incomplete or has broken sources.')
            with ap.EnvManager(addOutputsToMap=False):
                added = target.addLayer(layer_file, 'TOP')
            status['added_layers'] = [layer.name for layer in added]
            if len(added) != 5 or any(layer.isBroken for layer in added):
                raise RuntimeError('Not all five result layers were added correctly.')
            log_file.write('AFTER adding five prepared layers to CURRENT map\n')
        status['state'] = 'succeeded'
        status['project_saved'] = False
        write_status()
        print(f'DONE: five layers added to your existing map "{target.name}".', flush=True)
        print('Press Ctrl+S to save this same project when ready.', flush=True)
        print(f'Outputs: {run / "outputs"}', flush=True)
        return str(run)
    except Exception as error:
        status['state'] = 'failed'
        status['error'] = str(error)
        write_status()
        print(f'FAILED: {error}', flush=True)
        print(f'Saved outputs/logs remain in: {run}', flush=True)
        print('If layers were prepared, use Add Data with Watershed_Results.lyrx.', flush=True)
        raise


watershed_run_folder = watershed_in_current_project()
