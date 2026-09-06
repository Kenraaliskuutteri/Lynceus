const http = require('http');
const { WebSocketServer } = require('ws');
const { URL } = require('url');

const rooms = new Map();

function getRoom(id) {
  if (!rooms.has(id)) {
    rooms.set(id, { sockets: new Set(), lastSeen: null });
  }
  return rooms.get(id);
}

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Methods', '*');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.url === '/api/v1/servers') {
    const now = Date.now();
    const nodes = Array.from(rooms.entries()).map(([id, room]) => ({
      id,
      hostname: id,
      ipAddress: 'unknown',
      status: room.lastSeen && now - room.lastSeen < 10000 ? 'online' : 'offline',
      lastSeen: room.lastSeen ? new Date(room.lastSeen).toISOString() : null,
      metrics: null,
    }));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(nodes));
    return;
  }

  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (req, socket, head) => {
  const { pathname } = new URL(req.url, 'http://localhost');
  const match = pathname.match(/^\/api\/v1\/ws\/metrics\/([^/]+)$/);

  if (!match) {
    socket.destroy();
    return;
  }

  const id = match[1];

  wss.handleUpgrade(req, socket, head, (ws) => {
    const room = getRoom(id);
    room.sockets.add(ws);
    console.log(`socket joined room ${id} (${room.sockets.size} connected)`);

    ws.on('message', (data) => {
      room.lastSeen = Date.now();
      for (const peer of room.sockets) {
        if (peer !== ws && peer.readyState === peer.OPEN) {
          peer.send(data.toString());
        }
      }
    });

    ws.on('close', () => {
      room.sockets.delete(ws);
      console.log(`socket left room ${id} (${room.sockets.size} connected)`);
    });
  });
});

server.listen(8000, '0.0.0.0', () => console.log('relay server on :8000'));