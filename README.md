# Aroma
Video chatting with a dash of telecreativity. It is an exploration as to how to enable creativity in a virtual environment. 

## Instructions
Requires: nodejs and npm

1) npm install
2) npm run dev [developing] or npm start [production]
4) It will be available on locahost:5000 by default

## Planned feature set
- 1-1 videocalls
- Whiteboard functionality: Enable drawing on the screen without touch input (finger tracking using machine vision)
- Emotion dependent style transfer: Use bio signals to classify the emotional state of the user. The output video will be styled using neural styling based on the emotion detected.

## Implementation

Currently, it will be using WebRTC to enable 1-1 videochats, handled by a central NodeJS server. A Python server will run machine vision / neural styling algorithms on the WebRTC MediaStream.
