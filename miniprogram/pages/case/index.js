const { request } = require('../../utils/api')

const STATUS_ZH = {
  NEW: '待处理', DRAFTING: '拟稿中', PENDING_APPROVAL: '代理审核中',
  SENT_TO_BROKER: '已转交承运商', POSTED_TO_CUSTOMER: '已回复您', AWAITING_BROKER: '等待承运商回复',
  REPLY_DRAFTED: '拟回复中', RESOLVED: '已解决', CLOSED: '已关闭'
}

Page({
  data: { id: '', caseInfo: {}, statusZh: '', updates: [] },
  onLoad(options) { this.setData({ id: (options && options.id) || '' }) },
  onShow() {
    if (!this.data.id) return
    request('GET', '/cases/' + this.data.id).then(res => {
      const c = res.case || {}
      // The server already returns only approved app/zh updates to a customer; belt-and-suspenders
      // filter kept in case the caller is an agent-role viewer.
      const updates = (res.messages || []).filter(
        m => m.channel === 'app' && m.lang === 'zh' && m.status === 'posted')
      this.setData({ caseInfo: c, statusZh: STATUS_ZH[c.status] || c.status, updates })
    }).catch(() => {})
  }
})
