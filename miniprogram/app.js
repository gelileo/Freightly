App({
  globalData: {
    // Direct-to-US-domain (MVP). This host MUST be registered in the Mini Program request
    // allowlist (mp.weixin.qq.com → 开发管理 → 服务器域名) and served over HTTPS.
    baseUrl: 'https://api.example.com',
    token: ''
  },
  onLaunch() {
    this.globalData.token = wx.getStorageSync('session_token') || ''
  }
})
