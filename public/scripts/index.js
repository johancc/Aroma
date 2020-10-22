const serverHostName = 'https://viral-aroma.herokuapp.com:8080';
let isAlreadyCalling = false;
let getCalled = false;

const existingCalls = [];

const { RTCPeerConnection, RTCSessionDescription } = window;

var config = {
  sdpSemantics: 'unified-plan'
};
const peerConnection = new RTCPeerConnection(config);

function unselectUsersFromList() {
  const alreadySelectedUser = document.querySelectorAll(
    ".active-user.active-user--selected"
  );

  alreadySelectedUser.forEach(el => {
    el.setAttribute("class", "active-user");
  });
}

function createUserItemContainer(socketId) {
  const userContainerEl = document.createElement("div");

  const usernameEl = document.createElement("p");

  userContainerEl.setAttribute("class", "active-user");
  userContainerEl.setAttribute("id", socketId);
  usernameEl.setAttribute("class", "username");
  usernameEl.innerHTML = `Socket: ${socketId}`;

  userContainerEl.appendChild(usernameEl);

  userContainerEl.addEventListener("click", () => {
    unselectUsersFromList();
    userContainerEl.setAttribute("class", "active-user active-user--selected");
    const talkingWithInfo = document.getElementById("talking-with-info");
    talkingWithInfo.innerHTML = `Talking with: "Socket: ${socketId}"`;
    callUser(socketId, true, "rotate");
  });

  return userContainerEl;
}

async function callUser(socketId, is_caller, mode) {
  // const offer = await peerConnection.createOffer();
  // console.log("setting local description")
  // await peerConnection.setLocalDescription(new RTCSessionDescription(offer));
  // await peerConnection.setLocalDescription(offer);
  

  // socket.emit("call-user", {
  //   offer,
  //   to: socketId
  // });
  // this fetch below is an attempt to do something similar to https://github.com/aiortc/aiortc/blob/ea116d073129a022805b0a0741ae82a68c4cf3ca/examples/server/client.js#L84

  return peerConnection.createOffer().then(function(offer) {
      return peerConnection.setLocalDescription(offer);
  }).then(function() {
          // wait for ICE gathering to complete
          return new Promise(function(resolve) {
              if (peerConnection.iceGatheringState === 'complete') {
                  resolve();
              } else {
                  function checkState() {
                      if (peerConnection.iceGatheringState === 'complete') {
                          peerConnection.removeEventListener('icegatheringstatechange', checkState);
                          resolve();
                      }
                  }
                  peerConnection.addEventListener('icegatheringstatechange', checkState);
              }
          });
  }).then(function(){
    var offerReceived = peerConnection.localDescription;
    return fetch('/call-user', { 
      body: JSON.stringify({
        sdp: offerReceived.sdp,
        type: offerReceived.type, 
        video_transform: mode, //TODO: need to make it interactive, not hardcode
        is_caller: is_caller,
        offer: offerReceived,
        to: socketId,
        from: socket.id
      }),
      headers:{
        'Content-Type': "application/json",
      },
      method: 'POST'
    })
  })
  .then(function(response){
    return response.json()
  }).then(function(answer){
    // console.log("Got answer: sdp: "+answer.sdp + " type: "+ answer.type)
    console.log("setting remote description")
    return peerConnection.setRemoteDescription(answer);
  }).catch(function(e){
    alert(e);
  })

}

function updateUserList(socketIds) {
  const activeUserContainer = document.getElementById("active-user-container");

  socketIds.forEach(socketId => {
    const alreadyExistingUser = document.getElementById(socketId);
    if (!alreadyExistingUser) {
      const userContainerEl = createUserItemContainer(socketId);

      activeUserContainer.appendChild(userContainerEl);
    }
  });
}

const socket = io.connect(serverHostName);

socket.on("update-user-list", ({ users }) => {
  updateUserList(users);
});

socket.on("create-connection", async data =>{
  await callUser(data.from, false, "edges");
})
socket.on("remove-user", ({ socketId }) => {
  const elToRemove = document.getElementById(socketId);

  if (elToRemove) {
    elToRemove.remove();
  }
});

socket.on("call-made", async data => {
  // if (getCalled) {
  //   const confirmed = confirm(
  //     `User "Socket: ${data.socket}" wants to call you. Do accept this call?`
  //   );

  //   if (!confirmed) {
  //     socket.emit("reject-call", {
  //       from: data.socket
  //     });

  //     return;
  //   }
  // }
  console.log("receiver setting remote description")
  await peerConnection.setRemoteDescription(
    new RTCSessionDescription(data.offer)
  );
  const answer = await peerConnection.createAnswer();
  console.log("receiver setting local description")
  await peerConnection.setLocalDescription(new RTCSessionDescription(answer));

  socket.emit("make-answer", {
    answer,
    to: data.socket
  });
  getCalled = true;
});

socket.on("answer-made", async data => {
  console.log("caller setting remote description")
  await peerConnection.setRemoteDescription(
    new RTCSessionDescription(data.answer)
  );

  if (!isAlreadyCalling) {
    callUser(data.socket);
    isAlreadyCalling = true;
  }
});

socket.on("call-rejected", data => {
  alert(`User: "Socket: ${data.socket}" rejected your call.`);
  unselectUsersFromList();
});

// connect audio / video
peerConnection.addEventListener('track', function(evt) {
  console.log("getting track...")
  if (evt.track.kind == 'video'){
      document.getElementById('remote-video').srcObject = evt.streams[0];
  }
  else
      document.getElementById('audio').srcObject = evt.streams[0];
});
// peerConnection.ontrack = function({ streams: [stream] }) {
//   const remoteVideo = document.getElementById("remote-video");
//   if (remoteVideo) {
//     remoteVideo.srcObject = stream;
//   }
// };

navigator.getUserMedia(
  { video: true, audio: true },
  stream => {
    const localVideo = document.getElementById("local-video");
    if (localVideo) {
      localVideo.srcObject = stream;
    }

    stream.getTracks().forEach(track => peerConnection.addTrack(track, stream));
  },
  error => {
    console.warn(error.message);
  }
);
