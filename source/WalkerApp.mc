using Toybox.WatchUi as Ui;
using Toybox.Application as App;

class WalkerApp extends App.AppBase {
	
	var mainView;
	
	function initialize() {
		AppBase.initialize();
	}

	function onStop(state) {
		if (mainView != null) {
			// Store current step counts for later usage (e.g., resume later)
			if (Application has :Properties) {
				try {
					Application.Properties.setValue("as", mainView.steps);
					Application.Properties.setValue("ls", mainView.activityStepsAtPreviousLap);
				} catch (e) {
					// ignore
				}
			} else {
				var app = App.getApp();
				app.setProperty("as", mainView.steps);
				app.setProperty("ls", mainView.activityStepsAtPreviousLap);
			}
		}
	}
	
	function onSettingsChanged() {
		if (mainView != null) {
			mainView.readSettings();
			Ui.requestUpdate();
		}
	}
	
	function getInitialView() {
		mainView = new WalkerView();
		return [mainView];
	}

}