const { request } = require('../../utils/api')

Page({
  data: { busy: false, err: '' },
  login() {
    this.setData({ busy: true, err: '' })
    wx.login({
      success: ({ code }) => {
        request('POST', '/auth/wechat/login', { js_code: code }).then(res => {
          const app = getApp()
          app.globalData.token = res.session_token
          wx.setStorageSync('session_token', res.session_token)
          wx.reLaunch({ url: res.needs_bind ? '/pages/bind/index' : '/pages/cases/index' })
        }).catch(() => this.setData({ busy: false, err: '登录失败，请重试' }))
      },
      fail: () => this.setData({ busy: false, err: '微信登录失败' })
    })
  }
})
