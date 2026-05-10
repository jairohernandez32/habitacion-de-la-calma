#include <Adafruit_NeoPixel.h>
#include <avr/power.h>

#define PIN 6
#define NUMPIXELS      8

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

uint8_t counter = 0;
bool ejecutarLatido = false;
bool ejecutarWipe = false;
bool ejecutarTheaterChase = false;


void setup() {
  pixels.begin();
  Serial.begin(9600);
  pixels.setBrightness(100);
}

void loop() {
  
  int delayval = 50;
  
  uint32_t amarillo = pixels.Color(150, 150, 0);
  uint32_t rojopast = pixels.Color(236, 64, 122);
  uint32_t celeste = pixels.Color(0, 150, 150);
  uint32_t azul = pixels.Color(0, 0, 150);
  uint32_t morado = pixels.Color(150, 0, 150);
  uint32_t blanco = pixels.Color(150, 150, 150);

  uint32_t bandera;

  if(Serial.available()>0){
    char valor=Serial.read();

    switch(valor){
      case 'r':  
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(rojopast);
        pixels.show();  
        bandera = rojopast; 
        break;

      case 'c':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(celeste);
        pixels.show();
        bandera = celeste; 
        break;

      case 'b':
        ejecutarLatido = false;  
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(blanco);
        pixels.show();
        bandera = blanco;    
        break;

      case 'a':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(amarillo);
        pixels.show();
        bandera = amarillo; 
        break;

      case 'z':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(azul);
        pixels.show();
        bandera = azul; 
        break;
      
      case 'm':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.fill(morado);
        pixels.show();
        bandera = morado; 
        break;

      case 'l':
        // Activar el modo latido
        ejecutarLatido = true;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        break;

      case 'w':
        ejecutarLatido = false;
        ejecutarWipe = true;
        ejecutarTheaterChase = false;
        break;

      case 't':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = true;
        break;
        
      case 'k':
        ejecutarLatido = false;
        ejecutarWipe = false;
        ejecutarTheaterChase = false;
        pixels.Color(0, 0, 0);
        pixels.show();
        break;
    }
  }

  // Bucle para el efecto latido que se ejecuta continuamente
  if(ejecutarLatido) {
    efectoLatido(bandera);
  }
  
  if(ejecutarWipe) {
    colorWipe(bandera, 300);    
    colorWipe(pixels.Color(0, 0, 0), 300);
  }
    
  if(ejecutarTheaterChase) {
    theaterChaseContinuous(bandera, 300);
  }
  
}
  


// Función para barrido de color
void colorWipe(uint32_t color, int wait) {
  for(int i = 0; i < pixels.numPixels(); i++) {
    pixels.setPixelColor(i, color);
    pixels.show();
    delay(wait);
  }
}

// Función para efecto teatro
// Theater Chase en bucle continuo
void theaterChaseContinuous(uint32_t color, int wait) {
  for(int b = 0; b < 3; b++) {
    // Verificar si debemos seguir ejecutando
    if(!ejecutarTheaterChase) return;
    
    pixels.clear();
    for(int c = b; c < pixels.numPixels(); c += 3) {
      pixels.setPixelColor(c, color);
    }
    pixels.show();
    delay(wait);
  }
}

void theaterChase(uint32_t color, int wait) {
  for(int a = 0; a < 10; a++) {
    for(int b = 0; b < 3; b++) {
      pixels.clear();
      for(int c = b; c < pixels.numPixels(); c += 3) {
        pixels.setPixelColor(c, color);
      }
      pixels.show();
      delay(wait);
    }
  }
}

void efectoLatido(uint32_t color) {
  uint8_t beat = 128 + 127 * sin(counter * 0.1);
  counter++;
  
  // Extraer componentes RGB del color
  uint8_t r = (color >> 16) & 0xFF;
  uint8_t g = (color >> 8) & 0xFF;
  uint8_t b = color & 0xFF;
  
  for(int i = 0; i < NUMPIXELS; i++) {
    uint8_t attenuation = map(i, 0, NUMPIXELS-1, 100, 20);
    uint8_t brightness = (beat * attenuation) / 100;
    
    // Aplicar el color con el brillo calculado
    pixels.setPixelColor(i, (r * brightness) / 255, 
                            (g * brightness) / 255, 
                            (b * brightness) / 255);
  }
  pixels.show();
  delay(30);
}
