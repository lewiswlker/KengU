const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    allowedHosts: 'all',  // 允许所有主机访问（包括内网穿透域名）
    host: '0.0.0.0',      // 监听所有网络接口
    port: 8080,
    client: {
      webSocketURL: 'auto://0.0.0.0:0/ws'  // 自动处理 WebSocket 连接
    }
  }
})