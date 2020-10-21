/*
DEPRECATED:
Initial implementation of the webserver in TypeScript. 
Replaced with the Python server so Numpy, PyTorch, and 
OpenCV functions are better supported.
*/
import { Server } from './server';

const server = new Server();

server.listen(port => {
    console.log(`Server is listening on ${port}`);
});