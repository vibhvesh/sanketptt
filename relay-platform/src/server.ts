import Fastify from "fastify";
import helmet from "@fastify/helmet";
import cors from "@fastify/cors";
import rateLimit from "@fastify/rate-limit";
import Redis from "ioredis";
import { z } from "zod";
import { randomUUID, timingSafeEqual, createHash } from "node:crypto";

const env = z.object({
  PORT: z.coerce.number().default(8080),
  REDIS_URL: z.string().default("redis://127.0.0.1:6379"),
  DEVICE_TOKEN: z.string().min(24),
  FLOOR_LEASE_MS: z.coerce.number().int().min(1000).max(15000).default(5000),
  CORS_ORIGIN: z.string().default(""),
}).parse(process.env);

const app = Fastify({ logger: true, trustProxy: false, bodyLimit: 16 * 1024 });
const redis = new Redis(env.REDIS_URL, { maxRetriesPerRequest: 2, enableReadyCheck: true });
const tokenHash = createHash("sha256").update(env.DEVICE_TOKEN).digest();

await app.register(helmet);
await app.register(cors, { origin: env.CORS_ORIGIN ? env.CORS_ORIGIN.split(",") : false });
await app.register(rateLimit, { max: 120, timeWindow: "1 minute" });

app.addHook("onRequest", async (request, reply) => {
  if (request.url.startsWith("/health/")) return;
  const header = request.headers.authorization ?? "";
  const supplied = header.startsWith("Bearer ") ? header.slice(7) : "";
  const suppliedHash = createHash("sha256").update(supplied).digest();
  if (!supplied || !timingSafeEqual(tokenHash, suppliedHash)) {
    return reply.code(401).send({ error: "UNAUTHENTICATED", requestId: request.id });
  }
});

app.get("/health/live", async () => ({ status: "alive" }));
app.get("/health/ready", async (_request, reply) => {
  try { await redis.ping(); return { status: "ready" }; }
  catch { return reply.code(503).send({ status: "not_ready" }); }
});

const channelParams = z.object({ channelId: z.string().regex(/^[a-zA-Z0-9_-]{1,64}$/) });
const deviceBody = z.object({ deviceId: z.string().min(1).max(80), tenantId: z.string().min(1).max(80) });

app.get("/api/v1/channels", async () => ({
  channels: [{ id: "master", label: "Master", media: "webrtc-opus" }],
  note: "Bootstrap example only; production channels must be loaded from tenant-scoped storage."
}));

app.post("/api/v1/channels/:channelId/floor/request", async (request, reply) => {
  const params = channelParams.safeParse(request.params);
  const body = deviceBody.safeParse(request.body);
  if (!params.success || !body.success) return reply.code(400).send({ error: "INVALID_REQUEST" });
  const { channelId } = params.data;
  const { deviceId, tenantId } = body.data;
  const key = `floor:${tenantId}:${channelId}`;
  const leaseId = randomUUID();
  const granted = await redis.set(key, JSON.stringify({ deviceId, leaseId }), "PX", env.FLOOR_LEASE_MS, "NX");
  if (granted !== "OK") {
    const current = await redis.get(key);
    return reply.code(409).send({ status: "BUSY", channelId, currentTalker: current ? JSON.parse(current).deviceId : null });
  }
  return { status: "GRANTED", channelId, leaseId, leaseMs: env.FLOOR_LEASE_MS };
});

app.post("/api/v1/channels/:channelId/floor/renew", async (request, reply) => {
  const params = channelParams.safeParse(request.params);
  const body = z.object({ tenantId: z.string(), deviceId: z.string(), leaseId: z.string().uuid() }).safeParse(request.body);
  if (!params.success || !body.success) return reply.code(400).send({ error: "INVALID_REQUEST" });
  const key = `floor:${body.data.tenantId}:${params.data.channelId}`;
  const raw = await redis.get(key);
  if (!raw) return reply.code(409).send({ error: "FLOOR_LEASE_EXPIRED" });
  const current = JSON.parse(raw);
  if (current.deviceId !== body.data.deviceId || current.leaseId !== body.data.leaseId) return reply.code(403).send({ error: "FORBIDDEN" });
  const renewed = await redis.pexpire(key, env.FLOOR_LEASE_MS);
  if (!renewed) return reply.code(409).send({ error: "FLOOR_LEASE_EXPIRED" });
  return { status: "RENEWED", leaseMs: env.FLOOR_LEASE_MS };
});

app.post("/api/v1/channels/:channelId/floor/release", async (request, reply) => {
  const params = channelParams.safeParse(request.params);
  const body = z.object({ tenantId: z.string(), deviceId: z.string(), leaseId: z.string().uuid() }).safeParse(request.body);
  if (!params.success || !body.success) return reply.code(400).send({ error: "INVALID_REQUEST" });
  const key = `floor:${body.data.tenantId}:${params.data.channelId}`;
  const raw = await redis.get(key);
  if (!raw) return { status: "ALREADY_RELEASED" };
  const current = JSON.parse(raw);
  if (current.deviceId !== body.data.deviceId || current.leaseId !== body.data.leaseId) return reply.code(403).send({ error: "FORBIDDEN" });
  await redis.del(key);
  return { status: "RELEASED" };
});

app.addHook("onClose", async () => { await redis.quit(); });
await app.listen({ host: "0.0.0.0", port: env.PORT });
