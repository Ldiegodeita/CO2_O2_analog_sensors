#include <Arduino.h>
#include <SensirionI2CScd4x.h>
#include <Wire.h>
#include <SoftwareSerial.h>

SensirionI2CScd4x scd4x;

const int rxPin = 8;  // Pin 8 conectado a TX de LuminOx
const int txPin = 9;  // Pin 9 conectado a RX de LuminOx
const int sensorAnalogPin = A0;  // Pin para el sensor analógico

SoftwareSerial mySerial(rxPin, txPin);

// Variables para almacenar los valores de los sensores
int sensorAnalogValue = 0;
uint16_t co2 = 0;
float temperature = 0.0f;
float humidity = 0.0f;
String luminoxPercentage = "";

// Variables de tiempo
unsigned long previousMillis = 0;
const long interval = 5000;  // Intervalo de 5 segundos

void printUint16Hex(uint16_t value) {
    Serial.print(value < 4096 ? "0" : "");
    Serial.print(value < 256 ? "0" : "");
    Serial.print(value < 16 ? "0" : "");
    Serial.print(value, HEX);
}

void printSerialNumber(uint16_t serial0, uint16_t serial1, uint16_t serial2) {
    Serial.print("Serial: 0x");
    printUint16Hex(serial0);
    printUint16Hex(serial1);
    printUint16Hex(serial2);
    Serial.println();
}

void sendCommand(String command) {
    command += "\r\n";
    mySerial.print(command);
}

void setup() {
    // Iniciar la comunicación serial
    Serial.begin(115200);
    while (!Serial) {
        delay(300);
    }

    // Iniciar la comunicación I2C
    Wire.begin();
    
    // Iniciar el sensor SCD40
    uint16_t error;
    char errorMessage[256];

    scd4x.begin(Wire);
    error = scd4x.stopPeriodicMeasurement();
    if (error) {
        Serial.print("Error trying to execute stopPeriodicMeasurement(): ");
        errorToString(error, errorMessage, 256);
        Serial.println(errorMessage);
    }

    uint16_t serial0, serial1, serial2;
    error = scd4x.getSerialNumber(serial0, serial1, serial2);
    if (error) {
        Serial.print("Error trying to execute getSerialNumber(): ");
        errorToString(error, errorMessage, 256);
        Serial.println(errorMessage);
    } else {
        printSerialNumber(serial0, serial1, serial2);
    }

    error = scd4x.startPeriodicMeasurement();
    if (error) {
        Serial.print("Error trying to execute startPeriodicMeasurement(): ");
        errorToString(error, errorMessage, 256);
        Serial.println(errorMessage);
    }

    Serial.println("Waiting for first measurement... (5 sec)");

    // Iniciar la comunicación serial para el sensor LuminOx
    mySerial.begin(9600);
    pinMode(rxPin, INPUT);
    pinMode(txPin, OUTPUT);
}

void loop() {
    String cadena = "";
    char c;
    String valor = "";
    unsigned long currentMillis = millis();

    // Leer el valor del sensor analógico
    sensorAnalogValue = analogRead(sensorAnalogPin);

    // Leer datos del sensor SCD40 si ha pasado el intervalo de 5 segundos
    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;
        
        uint16_t error;
        char errorMessage[256];
        bool isDataReady = false;
        
        error = scd4x.getDataReadyFlag(isDataReady);
        if (error) {
            Serial.print("Error trying to execute getDataReadyFlag(): ");
            errorToString(error, errorMessage, 256);
            Serial.println(errorMessage);
        }
        
        if (isDataReady) {
            error = scd4x.readMeasurement(co2, temperature, humidity);
            if (error) {
                Serial.print("Error trying to execute readMeasurement(): ");
                errorToString(error, errorMessage, 256);
                Serial.println(errorMessage);
            }
        }

        // Mostrar los valores de los tres sensores en el monitor serial
        if (co2 != 0) {
            Serial.print(millis());
            Serial.print(", A0, ");
            Serial.print(sensorAnalogValue);
            Serial.print(", CO2, ");
            Serial.print(co2);
            Serial.print(", %O, ");
            Serial.println(luminoxPercentage);
        }
    }

    // Leer y almacenar datos del sensor LuminOx
    while (mySerial.available() > 0) {
        c = mySerial.read();
        //Serial.print(c); // Depurar: imprimir cada carácter recibido
        cadena += c;

        if (c == '\n') {
            break; // Salir del bucle si se encuentra "\r\n"
        }        
    }

    int pos = cadena.indexOf('%');
    if (pos != -1 && pos + 8 < cadena.length()) {
        luminoxPercentage = cadena.substring(pos + 1, pos + 8);
        luminoxPercentage.trim();
        // Serial.print("Luminox Percentage: ");
        // Serial.println(luminoxPercentage);
    }

    delay(1000);
    
    // Leer y enviar comandos al sensor LuminOx desde el monitor serial
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\r\n');
        sendCommand(command);
    }
}
