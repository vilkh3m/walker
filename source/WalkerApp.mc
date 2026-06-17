using Toybox.WatchUi as Ui;
using Toybox.Application as App;

class WalkerApp extends App.AppBase {
	
	var mainView;
	
	function initialize() {
		AppBase.initialize();
	}

	function onStop(state) {
		if (mainView != null) {
			try {
				if (Application has :Properties) {
					Application.Properties.setValue("as", mainView.steps);
					Application.Properties.setValue("ls", mainView.activityStepsAtPreviousLap);
				} else {
					var app = App.getApp();
					if (app != null) {
						app.setProperty("as", mainView.steps);
						app.setProperty("ls", mainView.activityStepsAtPreviousLap);
					}
				}
			} catch (e) {
				// ignore
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