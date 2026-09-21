# multi-stage: ชั้น build มี node_modules ครบ แต่ชั้นสุดท้ายเอาไปแค่ผลลัพธ์
# image เลยเล็กกว่าเอา node_modules ไปทั้งก้อนหลายเท่า
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
# standalone รวมเฉพาะไฟล์ที่ใช้จริงมาให้แล้ว
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app && chown -R app:app /app
USER app
EXPOSE 3000
CMD ["node", "server.js"]
