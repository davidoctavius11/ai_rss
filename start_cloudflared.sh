#!/bin/bash

# 设置API令牌
export CLOUDFLARE_API_TOKEN="UfsHQTxLEjKTLCtbIZmF1bvN3HYYjXD30zhu-IaS"
export TUNNEL_ORIGIN_CERT="$HOME/.cloudflared/cert.pem"

echo "启动Cloudflare Tunnel..."
echo "隧道名称: ai-rss-tunnel"
echo "子域名: rss.borntofly.ai"
echo "本地端口: 5003"

# 在后台运行Cloudflare Tunnel
nohup cloudflared tunnel --config /Users/ioumvp/ai_rss/cloudflared-config.yml run ai-rss-tunnel > /Users/ioumvp/ai_rss/cloudflared.log 2>&1 &

echo "Cloudflare Tunnel已启动，日志文件: /Users/ioumvp/ai_rss/cloudflared.log"
echo "检查隧道状态: cloudflared tunnel info ai-rss-tunnel"
echo "停止隧道: pkill -f 'cloudflared tunnel'"