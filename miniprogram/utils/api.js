// Thin JSON client over the app API. Attaches the session token as a Bearer header; on 401 it
// clears the stored token and returns to login (which re-runs wx.login). The AppSecret never
// lives here — the Mini Program only ever sends js_code and, later, the session token.
function request(method, path, body) {
  const app = getApp()
  const header = { 'Content-Type': 'application/json' }
  if (app.globalData.token) header['Authorization'] = 'Bearer ' + app.globalData.token
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.baseUrl + path,
      method: method,
      header: header,
      data: body || {},
      success(res) {
        if (res.statusCode === 401) {
          app.globalData.token = ''
          wx.removeStorageSync('session_token')
          wx.reLaunch({ url: '/pages/login/index' })
          reject(res.data || res)
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(res.data || res)
      },
      fail: reject
    })
  })
}

module.exports = { request }
