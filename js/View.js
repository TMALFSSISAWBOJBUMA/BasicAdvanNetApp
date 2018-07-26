function View(controller) {
    this.controller = controller;

    this.readerIP = null;
    this.initializeListeners();
}

View.prototype.initializeListeners = function() {

    var that = this;

    // Connect button
    var connectBtn = document.getElementById("connectBtn");
    connectBtn.addEventListener("click", function (event) {
        that.connectToReader();
    });

    // Start/stop button
    var startStopButton = document.getElementById("startStopButton");
    startStopButton.addEventListener("click", function (event) {
        that.toggleStartStop(startStopButton);
    });

    // Save button
    var saveBtn = document.getElementById("saveBtn");
    saveBtn.addEventListener("click", function(event) {
        var values = that.getValuesToSave();
        that.controller.saveSettings(values);
    });

    //sliders
    var powerBtn = document.getElementById("power");
    powerBtn.addEventListener("input", function (event) {
        that.updateRangeLabel("powerVal", this.value);
    });

    var sensBtn = document.getElementById("sensitivityRange");
    sensBtn.addEventListener("input", function (event) {
        that.updateRangeLabel("sensVal", this.value);
    });

    var volumeBtn = document.getElementById("volumeRange");
    volumeBtn.addEventListener("input", function (event) {
        that.updateRangeLabel("volumeVal", this.value);
    });
}


View.prototype.toggleStartStop = function(startStopButton) {
    var action = startStopButton.innerHTML == "Stop" ? "stop" : "start";
    this.controller.updateReaderStatus(this.readerIP, action);
}

/* Connect to reader event */
View.prototype.connectToReader = function() {
    this.readerIP = document.getElementById("readerIP").value;
    this.controller.connectToReader(this.readerIP);
}

View.prototype.displayConnectionMessage = function(connectionResult) {

    switch (connectionResult) {
        case "invalidIP":
            this.displayOperationStatus("text-danger", "The IP is not valid");
            break;
        case "notConnected":
            this.displayOperationStatus("text-danger", "Unable to connect. Does the IP correspond to a reader?");
            break;
        case "connected":
            this.displayOperationStatus("text-success", "Connected.");
            break;
        default:
            this.displayOperationStatus("text-danger", "Unknown operation");
            break;
    }
}

// Display reader options default values on the interface
View.prototype.displayReaderValues = function(readerValues) {

    console.log(readerValues);

    // Status
    this.displayReaderStatus(readerValues.status);

    // Model
    this.updateDivValue("readerModel", readerValues.model);

    // Power
    this.setRangeMinValue("power", readerValues.minPower);
    this.setRangeMaxValue("power", readerValues.maxPower);
    this.setRangeValue("power", readerValues.readPower);
    this.updateRangeLabel("powerVal", readerValues.readPower);

    // Sensitivity
    this.setRangeMinValue("sensitivityRange", readerValues.maxSensitivity);
    this.setRangeMaxValue("sensitivityRange", readerValues.minSensitivity);
    this.setRangeValue("sensitivityRange", readerValues.sensitivity);
    this.updateRangeLabel("sensVal", readerValues.sensitivity);

    // Antennas
    this.displayAntennas(readerValues.numPorts, readerValues.activeAntennas);   

    // Volume
    this.setRangeMinValue("volumeRange", 1);
    this.setRangeMaxValue("volumeRange", 10);
    this.setRangeValue("volumeRange", readerValues.volume);
    this.updateRangeLabel("volumeVal", readerValues.volume);
}

// Display the range current value to give feedback to the user
View.prototype.updateRangeLabel = function(rangeLabel, value) {
    this.updateDivValue(rangeLabel, value);
}

// Set any range value
View.prototype.setRangeValue = function(range, value) {
    document.getElementById(range).value = value;
}

View.prototype.getRangeValue = function(range) {
    return document.getElementById(range).value;
}

// Set the minimum value of any range reader options
View.prototype.setRangeMinValue = function(range, minvalue) {
    document.getElementById(range).min = minvalue;
}

// Set the maximum value of any range reader options
View.prototype.setRangeMaxValue = function(range, maxvalue) {
    document.getElementById(range).max = maxvalue;
}

/*
    Pre: the ID of a div and the string we want inside the div
    Post: the string is written inside the div
*/
View.prototype.updateDivValue = function(divID, value) {
    document.getElementById(divID).innerHTML = value;
}

View.prototype.getDivValue = function(divID) {
    return document.getElementById(divID).innerHTML;
}

View.prototype.getActiveAntennas = function() {
    
    var activeAntennas = [];
    var antennasDiv = document.querySelector('#antennasList');
    var checkedBoxes = antennasDiv.querySelectorAll('input[type="checkbox"]:checked');

    for (var i = 0; i < checkedBoxes.length; i++) {
        var checkedID = checkedBoxes[i].id;
        var numPort = checkedID.substring(checkedID.length - 1);
        activeAntennas.push(numPort);
    }
    return activeAntennas;
}

/* 
    Pre: the number of RF ports of the reader and a vector with all the active antennas
    Post: displays all the reader antennas with a checked checkbox if the antenna is active or not checked otherwise
*/
View.prototype.displayAntennas = function(numPorts, activeAntennas) {
    var antennasList = document.getElementById("antennasList");

    antennasList.innerHTML = '<label for="antennas">Antennas:</label><br>';
    for (var port = 1; port <= numPorts; port++) {
        antennasList.innerHTML += 
            '<input class="form-check-input ml-4" type="checkbox" value="port' + port + '" id="antennaPort' + port + '" ' + this.isActiveAntenna(port, activeAntennas) + '>' +
            '<label class="form-check-label ml-5" for="antennaPort' + port + '">' +
                'Port ' + port +
            '</label>' +
            '<br>';
    }
}

/*
    Pre: an antenna port and all the active antennas
    Post: an string like "checked" if the antenna port is active or an empty string otherwise
*/
View.prototype.isActiveAntenna = function(port, activeAntennas) {
    for (var a in activeAntennas) {
        if (activeAntennas[a].port == port) 
            return "checked";
    }
    return "";
}

/*
    Pre: the status of the reader (running || stopped || connected || shutdown)
    Post: changes the color of the status background according to the reader status
*/
View.prototype.displayReaderStatus = function(status) {
    
    // Background and text to display
    var bg = null;
    var baseclasses = "alert ";
    var buttonText = null;

    switch (status) {
        case "RUNNING":
            bg = baseclasses + "alert-success";
            buttonText = "Stop";
            this.controller.startInventory(this.readerIP);
            break;
        case "STOPPED":
            bg = baseclasses + "alert-danger";
            buttonText = "Start";
            break;
        case "CONNECTED":
            bg = baseclasses + "alert-primary";
            buttonText = "Start";
            break;
        case "SHUTDOWN":
            bg = baseclasses + "alert-dark";
            buttonText = "Start";
            break;
        default:
            bg = baseclasses + "alert-light";
            buttonText = "Start";
            break;
    }

    document.getElementById("statusBg").className = bg;
    document.getElementById("statusText").innerHTML = status;
    document.getElementById("startStopButton").innerHTML = buttonText;
    document.getElementById("connectBtn").innerHTML = "Update";
}

View.prototype.displaySaveStatus = function(saveStatus) {

    switch (saveStatus) {
        case "OK":
            this.displayOperationStatus("alert-success", "Settings saved");
            break;
        default:
            this.displayOperationStatus("alert-danger", "Error saving settings");
            break;
    }
}

View.prototype.getValuesToSave = function() {
    return {
        power: this.getRangeValue("power"),
        sensitivity: this.getRangeValue("sensitivityRange"),
        antennas: this.getActiveAntennas(),
        volume: this.getRangeValue("volumeRange")
    }
}

View.prototype.displayOperationStatus = function(bg, text) {
    var div = document.getElementById("operationStatus");
    div.innerHTML = text;
    div.className = "alert " + bg;
}