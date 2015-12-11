#if defined(ARDUINO) && ARDUINO >= 100
  #include "Arduino.h"
#else
  #include "WProgram.h"
#endif
#include "bitlash.h"

const int p1PIN =  2;      // the number of the LED pin
const int p2PIN =  3;      // the number of the LED pin
const int p3PIN =  4;      // the number of the LED pin
const int p4PIN =  5;      // the number of the LED pin
const int sensePIN =  12;      // the number of the LED pin

// Declare a user function named "timer1" returning a numeric Bitlash value
//
numvar senseOFF(void) { 
  digitalWrite(sensePIN, LOW);
  Serial.println("Sense Power OFF");
}
numvar senseON(void) { 
  digitalWrite(sensePIN, HIGH);
  Serial.println("Sense Power ON");
}

numvar p1ON(void) { 
  digitalWrite(p1PIN, HIGH);
  Serial.println("Pump 1 ON");
}
numvar p2ON(void) { 
  digitalWrite(p2PIN, HIGH);
  Serial.println("Pump 2 ON");
}
void p3ON(void) { 
  digitalWrite(p3PIN, HIGH);
  Serial.println("Pump 3 ON");
}
void p4ON(void) { 
  digitalWrite(p4PIN, HIGH);
  Serial.println("Pump 4 ON");
}
void p1OFF(void) { 
  digitalWrite(p1PIN, LOW);
  Serial.println("Pump 1 OFF");
}
void p2OFF(void) { 
  digitalWrite(p2PIN, LOW);
  Serial.println("Pump 2 OFF");
}
void p3OFF(void) { 
  digitalWrite(p3PIN, LOW);
  Serial.println("Pump 3 OFF");
}
void p4OFF(void) { 
  digitalWrite(p4PIN, LOW);
  Serial.println("Pump 4 OFF");
}
numvar A0READ(void){
  return analogRead(A0);
}
numvar A1READ(void){
  return analogRead(A1);
}
numvar A2READ(void){
  return analogRead(A2);
}
numvar A3READ(void){
  return analogRead(A3);
}
numvar A4READ(void){
  return analogRead(A4);
}
numvar A5READ(void){
  return analogRead(A5);
}
numvar A6READ(void){
  return analogRead(A6);
}
numvar A7READ(void){
  return analogRead(A7);
}

void setup(void) {
  initBitlash(57600);   // must be first to initialize serial port

  // Register the extension function with Bitlash
  //    "timer1" is the Bitlash name for the function
  //    0 is the argument signature: takes 0 arguments
  //    (bitlash_function) timer1 tells Bitlash where our handler lives
  //

  pinMode(p1PIN, OUTPUT);
  pinMode(p2PIN, OUTPUT);
  pinMode(p3PIN, OUTPUT);
  pinMode(p4PIN, OUTPUT);
  pinMode(sensePIN, OUTPUT);

  
  digitalWrite(p1PIN, LOW);
  digitalWrite(p2PIN, LOW);
  digitalWrite(p3PIN, LOW);
  digitalWrite(p4PIN, LOW);
  digitalWrite(sensePIN, LOW);
  

  addBitlashFunction("senseon", (bitlash_function) senseON);
  addBitlashFunction("senseoff", (bitlash_function) senseOFF);
  
  addBitlashFunction("p1on", (bitlash_function) p1ON);
  addBitlashFunction("p2on", (bitlash_function) p2ON);
  addBitlashFunction("p3on", (bitlash_function) p3ON);
  addBitlashFunction("p4on", (bitlash_function) p4ON);
  addBitlashFunction("p1off", (bitlash_function) p1OFF);
  addBitlashFunction("p2off", (bitlash_function) p2OFF);
  addBitlashFunction("p3off", (bitlash_function) p3OFF);
  addBitlashFunction("p4off", (bitlash_function) p4OFF);

  addBitlashFunction("a0read", (bitlash_function) A0READ);
  addBitlashFunction("a1read", (bitlash_function) A1READ);
  addBitlashFunction("a2read", (bitlash_function) A2READ);
  addBitlashFunction("a3read", (bitlash_function) A3READ);
  addBitlashFunction("a4read", (bitlash_function) A4READ);
  addBitlashFunction("a5read", (bitlash_function) A5READ);
  addBitlashFunction("a6read", (bitlash_function) A6READ);
  addBitlashFunction("a7read", (bitlash_function) A7READ);

}

void loop(void) {
  runBitlash();
}
