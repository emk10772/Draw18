#include <Adafruit_STSPIN220.h>
#include <Servo.h>

// Pinouts
const int STEPS_PER_REVOLUTION = 200;
const int SERVO_PIN = 2;

const int STEP_PIN_1 = 5;
const int DIR_PIN_1 = 4;

const int STEP_PIN_2 = 11;
const int DIR_PIN_2 = 10;

// Creating stepper objects
Adafruit_STSPIN220 stepper1(STEPS_PER_REVOLUTION, STEP_PIN_1, DIR_PIN_1);
Adafruit_STSPIN220 stepper2(STEPS_PER_REVOLUTION, STEP_PIN_2, DIR_PIN_2);

// Define Servo
Servo penServo;
const int PEN_UP_ANGLE = 25;    
const int PEN_DOWN_ANGLE = 15;  

// Robot & board parameters
const float STEPS_PER_MM = (STEPS_PER_REVOLUTION*16) / (0.5 * PI * 25.4);  
const float WHITEBOARD_WIDTH = 490;
const float WHITEBOARD_HEIGHT = 855;

const float DRAW_WIDTH_MM = 200;
const float DRAW_HEIGHT_MM = 300;

const float OFFSET_X_MM = 145;
const float OFFSET_Y_MM = 350;  

// Init position
const float START_X_MM = OFFSET_X_MM;                      
const float START_Y_MM = OFFSET_Y_MM + DRAW_HEIGHT_MM;   
float current_position_x = START_X_MM;
float current_position_y = START_Y_MM;
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

  float initial_radius_L = sqrt(START_X_MM * START_X_MM + START_Y_MM * START_Y_MM);
  float initial_radius_R = sqrt(((WHITEBOARD_WIDTH - START_X_MM) * (WHITEBOARD_WIDTH - START_X_MM)) + (START_Y_MM * START_Y_MM));
  
  current_steps_L = (long)(initial_radius_L * STEPS_PER_MM);
  current_steps_R = (long)(initial_radius_R * STEPS_PER_MM);
  
  // Initialize servo
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE);
  delay(500);
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

  // Calculate string lengths from top corners
  float radius_L = sqrt(x_mm * x_mm + y_mm * y_mm);
  float radius_R = sqrt(((WHITEBOARD_WIDTH - x_mm) * (WHITEBOARD_WIDTH - x_mm)) + (y_mm * y_mm));

  // Convert to steps
  long target_steps_L = (long)(radius_L * STEPS_PER_MM);
  long target_steps_R = (long)(radius_R * STEPS_PER_MM);

  // Calculate how many steps to move
  long delta_L = target_steps_L - current_steps_L;
  long delta_R = target_steps_R - current_steps_R;

  // Get absolute values and directions
  long abs_L = abs(delta_L);
  long abs_R = abs(delta_R);
  int dir_L = (delta_L > 0) ? 1 : -1;
  int dir_R = (delta_R > 0) ? 1 : -1;

  // Find the maximum number of steps needed
  long max_steps = max(abs_L, abs_R);
  
  if (max_steps == 0) return; 

  // Bresenham for smoother stepping
  long error_L = max_steps / 2;
  long error_R = max_steps / 2;

  for (long i = 0; i < max_steps; i++) {
    // Accumulate error for left stepper
    error_L += abs_L;
    if (error_L >= max_steps) {
      stepper1.step(dir_L);
      current_steps_L += dir_L;
      error_L -= max_steps;
    }

    // Accumulate error for right stepper
    error_R += abs_R;
    if (error_R >= max_steps) {
      stepper2.step(dir_R);
      current_steps_R += dir_R;
      error_R -= max_steps;
    }
  }

  // Update current position
  current_position_x = x_mm;
  current_position_y = y_mm;
}
