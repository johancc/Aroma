import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import socketio
import jsonpickle 

import cv2
from aiohttp import web
from av import VideoFrame

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
existingSockets = []
pcs = []
# serverHostName = 'https://viral-aroma.herokuapp.com/'
sio = socketio.AsyncServer()

class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, transform):
        super().__init__()  # don't forget this!
        self.track = track
        self.transform = transform

    async def recv(self):
        frame = await self.track.recv()

        if self.transform == "cartoon":
            img = frame.to_ndarray(format="bgr24")

            # prepare color
            img_color = cv2.pyrDown(cv2.pyrDown(img))
            for _ in range(6):
                img_color = cv2.bilateralFilter(img_color, 9, 9, 7)
            img_color = cv2.pyrUp(cv2.pyrUp(img_color))

            # prepare edges
            img_edges = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            img_edges = cv2.adaptiveThreshold(
                cv2.medianBlur(img_edges, 7),
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                9,
                2,
            )
            img_edges = cv2.cvtColor(img_edges, cv2.COLOR_GRAY2RGB)

            # combine color and edges
            img = cv2.bitwise_and(img_color, img_edges)
            # img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        elif self.transform == "edges":
            # perform edge detection
            img = frame.to_ndarray(format="bgr24")
            img = cv2.cvtColor(cv2.Canny(img, 100, 200), cv2.COLOR_GRAY2BGR)

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        elif self.transform == "rotate":
            # rotate image
            img = frame.to_ndarray(format="bgr24")
            rows, cols, _ = img.shape
            M = cv2.getRotationMatrix2D((cols / 2, rows / 2), frame.time * 45, 1)
            img = cv2.warpAffine(img, M, (cols, rows))

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        else:
            return frame

async def index(request):
    content = open(os.path.join(ROOT, "../public/index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)
async def javascript(request):
    content = open(os.path.join(ROOT, "../public/scripts/index.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)
async def css(request):
    content = open(os.path.join(ROOT, "../public/styles.css"), "r").read()
    return web.Response(content_type="text/css", text=content)

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def offer(request):
    params = await request.json() # params should have sdp, type, video_transform
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    @pc.on("track") # ???
    def on_track(track):
        log_info("Track %s received", track.kind)

        if track.kind == "video":
            log_info(params["video_transform"])
            local_video = VideoTransformTrack(
                track, transform=params["video_transform"]
            )
            pc.addTrack(local_video)  
        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
    # handle offer
    await pc.setRemoteDescription(offer)
    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)    

    # await sio.emit("call-made", {
    #     "offer": params["offer"],
    #     "socket": params["from"]
    # }, to=params["to"])

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

##### Everything above here is from https://github.com/aiortc/aiortc/blob/main/examples/server/server.py ##########

#### Everything below is an attempt to recreate the functionality of server.ts #####

@sio.on("call-user")
async def callUser(sid, data):
    await sio.emit("call-made", {
        "offer": data["offer"],
        "socket": sid
    }, to=data["to"])

@sio.on("make-answer")
async def makeAnswer(sid, data):
    await sio.emit("answer-made", {
        "socket": sid,
        "answer": data["answer"]
    }, to = data["to"])

@sio.on("reject-call")
async def rejectCall(sid, data):
    await sio.emit("call-rejected", {
        "socket": sid
    }, to = data["from"])

@sio.event
async def connect(sid, data):
    # print(f"connected!, sid={sid} and data={data}")
    if sid not in existingSockets:
        await sio.emit("update-user-list", {
            "users": existingSockets
        }, to=sid)
        existingSockets.append(sid)
        await sio.emit("update-user-list", {
            "users": [sid]
        }, skip_sid=sid)

@sio.event
async def disconnect(sid):
    existingSockets.remove(sid)
    await sio.emit("remove-user", {
        "socketId": sid
    }, broadcast=True, include_self=True)

if __name__ == "__main__":
    host = 'localhost' #'127.0.0.1'
    port = 5000
    ssl_context = None
    #######################
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/styles.css", css)
    app.router.add_get("/scripts/index.js", javascript)
    app.router.add_post("/call-user", offer)
    sio.attach(app)
    web.run_app(
        app,
        access_log=None,
        host = host,
        port = port,
        ssl_context = ssl_context
    )  
