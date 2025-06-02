#include <Servo.h>
// --- Variables and Constants ---
Servo barrierServo;
bool gateOpen = false;
unsigned long lastBuzzTime = 0;
const unsigned long buzzInterval = 300;
bool buzzerState = false;
// --- Pin Definitions ---
#define TRIGGER_PIN     2
#define ECHO_PIN        3
#define RED_LED_PIN     4
#define BLUE_LED_PIN    5
#define SERVO_PIN       6
#define GND1_PIN        7
#define GND2_PIN        8
#define BUZZER_PIN      11
// --- Setup ---
void setup() {
  initializeSerial();
  initializeUltrasonic();
  initializeLEDs();
  initializeBuzzer();
  initializeExtraGNDs();
  initializeServo();
}
// --- Loop ---
void loop() {
  float distance = measureDistance();
  Serial.println(distance);
  handleSerialCommands();
  handleBuzzer();
  delay(50);
}
// --- Initialization Functions ---
void initializeSerial() {
  Serial.begin(9600);
}
void initializeUltrasonic() {
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}
void initializeLEDs() {
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(BLUE_LED_PIN, OUTPUT);
}
void initializeBuzzer() {
  pinMode(BUZZER_PIN, OUTPUT);
}
void initializeExtraGNDs() {
  pinMode(GND1_PIN, OUTPUT);
  pinMode(GND2_PIN, OUTPUT);
  digitalWrite(GND1_PIN, LOW);
  digitalWrite(GND2_PIN, LOW);
}
void initializeServo() {
  barrierServo.attach(SERVO_PIN);
  setGatePosition(10);
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(BLUE_LED_PIN, HIGH);
  delay(500);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(BLUE_LED_PIN, LOW);

}
// --- Serial Command Handling ---
void handleSerialCommands() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == '1') openGate();
    else if (cmd == '0') closeGate();
    else if (cmd == '2') buzzAlert();
  }
}
// --- Distance Measurement ---
float measureDistance() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  return (duration * 0.0343) / 2.0;  // in cm
}
// --- Servo Movement ---
void setGatePosition(int angle) {
  barrierServo.write(angle);
}
// --- Gate Actions ---
void openGate() {
  setGatePosition(90);
  gateOpen = true;
  digitalWrite(BLUE_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, LOW);
}
void closeGate() {
  setGatePosition(10);
  gateOpen = false;
  digitalWrite(BLUE_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, HIGH);
  delay(500);
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW); 
}
// --- Buzzer Handling ---
void handleBuzzer() {
  if (gateOpen) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastBuzzTime > buzzInterval) {
      buzzerState = !buzzerState;
      digitalWrite(BUZZER_PIN, buzzerState);
      lastBuzzTime = currentMillis;
    }
  }
}

void buzzAlert() {
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(RED_LED_PIN, HIGH);
  delay(1000);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
}