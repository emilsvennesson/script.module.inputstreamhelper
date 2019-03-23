import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import inputstreamhelper

ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')
LANGUAGE = ADDON.getLocalizedString

is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
orig_disabled = ADDON.getSetting('disabled')

ADDON.setSetting('disabled', 'false')

if len(sys.argv) == 2:
	if sys.argv[1] == "force_reinstall" and os.path.lexists(is_helper._widevine_config_path()):
		os.remove(is_helper._widevine_config_path())

if is_helper.check_inputstream():
	dialog = xbmcgui.Dialog()
	dialog.ok(LANGUAGE(30037), LANGUAGE(30003))

ADDON.setSetting('disabled', orig_disabled)
