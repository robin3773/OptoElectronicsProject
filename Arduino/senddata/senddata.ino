int resistor = 460; 

void setup() {
  Serial.begin(9600);
}

void loop() { 
  float val1 = analogRead(A0) * 5000000.0/ 1023.0;
  float val2 = analogRead(A1) * 5000000.0/ 1023.0; 
  float val3 = 1000* (val1 - val2) / resistor; 
  Serial.print(val1);
  Serial.print(" ");
  Serial.print(val2);
  Serial.print(" "); 
  Serial.println(val3);
  delay(1);
}
