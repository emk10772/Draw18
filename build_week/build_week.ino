#include <Adafruit_STSPIN220.h>
#include <Servo.h>

// Pinouts
const int STEPS_PER_REVOLUTION = 200;
const int SERVO_PIN = 9;

const int STEP_PIN_1 = 2;
const int DIR_PIN_1 = 3;

const int STEP_PIN_2 = 5;
const int DIR_PIN_2 = 4;

int totalMicrosteps = 0;

// Creating stepper objects
Adafruit_STSPIN220 stepper1(STEPS_PER_REVOLUTION, STEP_PIN_1, DIR_PIN_1);
Adafruit_STSPIN220 stepper2(STEPS_PER_REVOLUTION, STEP_PIN_2, DIR_PIN_2);

// Define Servo
Servo penServo;
const int PEN_UP_ANGLE = 90;    
const int PEN_DOWN_ANGLE = 60;  

// Robot parameters
const float STEPS_PER_MM = (STEPS_PER_REVOLUTION) / (0.5 * PI * 25.4);  
const float WHITEBOARD_WIDTH = 1753;
const float WHITEBOARD_HEIGHT = 1219;

// Init position
float current_position_x = 0.0;
float current_position_y = 0.0;
long current_steps_L = 0;  
long current_steps_R = 0;

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

  // Calculate string length from L/R corners of board
  long target_steps_L = (long) sqrt(x_mm * x_mm + y_mm * y_mm) * STEPS_PER_MM;
  long target_steps_R = (long) sqrt(((WHITEBOARD_WIDTH - x_mm) * (WHITEBOARD_WIDTH - x_mm)) + (y_mm * y_mm)) * STEPS_PER_MM;

  // Calculate how many steps to move
  long delta_steps_L = target_steps_L - current_steps_L;
  long delta_steps_R = target_steps_R - current_steps_R;

  // Executing movement commands
  if (delta_steps_L != 0) {
      stepper1.step(delta_steps_L);
  }
  
  if (delta_steps_R != 0) {
      stepper2.step(delta_steps_R);
  }

  // Update current position
  current_steps_L = target_steps_L;
  current_steps_R = target_steps_R;
  current_position_x = x_mm;
  current_position_y = y_mm;
}