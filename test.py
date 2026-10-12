import hoarder
import pathlib
from hoarder.passwords import SabnzbdPasswordPlugin, sabnzbd_password_plugin
from hoarder.phases.orchestrator import process_target
from hoarder.utils.path_utils import AnchoredPath
from hoarder.utils import pprint
from hoarder.phases.scan_target import ScanTarget

s_plugin = SabnzbdPasswordPlugin({})
p_store = s_plugin.extract_passwords()

corr_path = pathlib.Path('/mnt/ds423plus/usenet')
entry_path = pathlib.Path('test')
a_path = AnchoredPath(corr_path, entry_path)

scan_target = ScanTarget(a_path)
corr = process_target(scan_target, p_store)
pprint(corr)
