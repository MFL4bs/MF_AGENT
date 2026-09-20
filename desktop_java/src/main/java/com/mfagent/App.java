package com.mfagent;

import com.mfagent.controller.AppController;
import javafx.application.Application;
import javafx.stage.Stage;

public class App extends Application {

    @Override
    public void start(Stage primaryStage) {
        AppController controller = new AppController(primaryStage);
        controller.init();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
