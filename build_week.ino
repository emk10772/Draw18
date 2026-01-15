#include <Adafruit_STSPIN220.h>
#include <Servo.h>

// Defining constants
const int STEPS_PER_REVOLUTION = 200;
const int SERVO_PIN = 9;

const int STEP_PIN_1 = 2;
const int DIR_PIN_1 = 3;

const int STEP_PIN_2 = 5;
const int DIR_PIN_2 = 4;

int totalMicrosteps;

// Creating stepper objects
Adafruit_STSPIN220 stepper1(STEPS_PER_REVOLUTION, STEP_PIN_1, DIR_PIN_1);
Adafruit_STSPIN220 stepper2(STEPS_PER_REVOLUTION, STEP_PIN_2, DIR_PIN_2);

// Robot parameters
const float STEPS_PER_MM = (STEPS_PER_REVOLUTION) / (0.5 * PI * 25.4);  
const float WHITEBOARD_WIDTH = 1753;
const float WHITEBOARD_HEIGHT = 1219;

float current_position_x = 0.0;
float current_position_y = 0.0;
long current_steps_1 = 0;  
long current_steps_2 = 0;

Servo penServo;
const int PEN_UP_ANGLE = 90;    
const int PEN_DOWN_ANGLE = 60;  

void setup() {
  // Connecting serial
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  // Set microstepping mode
  stepper1.setStepMode(STSPIN220_STEP_1_16);
  stepper2.setStepMode(STSPIN220_STEP_1_16);
  
  totalMicrosteps = STEPS_PER_REVOLUTION * 16;
  
  // Initialize servo
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE);
  delay(500);
  
  // Starting at (0, 0) - top left corner
  current_steps_1 = 0;
  current_steps_2 = 0;
  
  Serial.println("Ready to receive commands");
}

void loop() {
  readSerial();
}

void readSerial() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "PEN_UP") {
      penServo.write(PEN_UP_ANGLE);
      delay(300);
      Serial.println("OK");
    }
    else if (cmd == "PEN_DOWN") {
      penServo.write(PEN_DOWN_ANGLE);
      delay(300);
      Serial.println("OK");
    }
    else if (cmd.startsWith("MOVE")) {
      int firstSpace = cmd.indexOf(' ');
      int secondSpace = cmd.indexOf(' ', firstSpace + 1);
      
      float x_mm = cmd.substring(firstSpace + 1, secondSpace).toFloat();
      float y_mm = cmd.substring(secondSpace + 1).toFloat();
      
      moveToXY(x_mm, y_mm);
      Serial.println("OK");
    }
  }
}

void moveToXY(float x_mm, float y_mm) {
  // Constrain position to be within whiteboard area
  x_mm = constrain(x_mm, 0, WHITEBOARD_WIDTH);
  y_mm = constrain(y_mm, 0, WHITEBOARD_HEIGHT);

  // Calculate string lengths
  float radius_1 = sqrt(x_mm * x_mm + y_mm * y_mm);
  float radius_2 = sqrt(((WHITEBOARD_WIDTH - x_mm) * (WHITEBOARD_WIDTH - x_mm)) + (y_mm * y_mm));

  // Convert to steps (microsteps)
  long target_steps_1 = (long)(radius_1 * STEPS_PER_MM);
  long target_steps_2 = (long)(radius_2 * STEPS_PER_MM);

  // Calculate how many steps to move
  long delta_steps_1 = target_steps_1 - current_steps_1;
  long delta_steps_2 = target_steps_2 - current_steps_2;

  // Executing movement commands
  if (delta_steps_1 != 0) {
    if (delta_steps_1 > 0) {
      stepper1.step(abs(delta_steps_1), FORWARD, STSPIN220_STEP_1_16);
    } else {
      stepper1.step(abs(delta_steps_1), BACKWARD, STSPIN220_STEP_1_16);
    }
  }
  
  if (delta_steps_2 != 0) {
    if (delta_steps_2 > 0) {
      stepper2.step(abs(delta_steps_2), FORWARD, STSPIN220_STEP_1_16);
    } else {
      stepper2.step(abs(delta_steps_2), BACKWARD, STSPIN220_STEP_1_16);
    }
  }

  // Update current position
  current_steps_1 = target_steps_1;
  current_steps_2 = target_steps_2;
  current_position_x = x_mm;
  current_position_y = y_mm;
}