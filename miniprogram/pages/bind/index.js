const { request } = require('../../utils/api')

Page({
  data: { code: '', busy: false, err: '' },
  onLoad(options) {
    // Entered via a 小程序码? The invite code arrives as the launch scene param.
    if (options && options.scene) this.setData({ code: decodeURIComponent(options.scene) })
  },
  onInput(e) { this.setData({ code: e.detail.value }) },
  bind() {
    if (!this.data.code) { this.setData({ err: '请输入邀请码' }); return }
    this.setData({ busy: true, err: '' })
    request('POST', '/auth/bind', { code: this.data.code })
      .then(() => wx.reLaunch({ url: '/pages/cases/index' }))
      .catch(() => this.setData({ busy: false, err: '邀请码无效或已使用' }))
  }
})
