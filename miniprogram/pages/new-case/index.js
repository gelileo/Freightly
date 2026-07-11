const { request } = require('../../utils/api')

Page({
  data: {
    engagements: [], engNames: [], engIdx: 0,
    brokers: [], brokerNames: [], brokerIdx: 0,
    issues: [], issueNames: [], issueIdx: 0,
    fields: [], fieldValues: {},
    bol: '', note: '', busy: false, err: ''
  },
  onLoad() {
    request('GET', '/engagements').then(res => {
      const engagements = res.engagements || []
      this.setData({ engagements, engNames: engagements.map(e => e.agent_name) })
      this.syncBrokers(0)
    }).catch(() => {})
    request('GET', '/issue-types').then(res => {
      const issues = res.issue_types || []
      this.setData({ issues, issueNames: issues.map(i => i.label_zh) })
      this.syncFields(0)
    }).catch(() => {})
  },
  onEng(e) { const i = +e.detail.value; this.setData({ engIdx: i }); this.syncBrokers(i) },
  syncBrokers(i) {
    const e = this.data.engagements[i]
    const brokers = (e && e.broker_accounts) || []
    this.setData({ brokers, brokerNames: brokers.map(b => b.broker_name), brokerIdx: 0 })
  },
  onBroker(e) { this.setData({ brokerIdx: +e.detail.value }) },
  onIssue(e) { const i = +e.detail.value; this.setData({ issueIdx: i }); this.syncFields(i) },
  syncFields(i) {
    const issue = this.data.issues[i]
    this.setData({ fields: (issue && issue.fields) || [], fieldValues: {} })
  },
  onBol(e) { this.setData({ bol: e.detail.value }) },
  onNote(e) { this.setData({ note: e.detail.value }) },
  onField(e) { this.setData({ ['fieldValues.' + e.currentTarget.dataset.name]: e.detail.value }) },
  submit() {
    const e = this.data.engagements[this.data.engIdx]
    if (!e) { this.setData({ err: '请选择代理' }); return }
    if (!this.data.bol) { this.setData({ err: '请填写 BOL' }); return }
    const broker = this.data.brokers[this.data.brokerIdx]
    const issue = this.data.issues[this.data.issueIdx]
    const fields = {}
    Object.keys(this.data.fieldValues).forEach(k => {
      const v = (this.data.fieldValues[k] || '').trim()
      if (v) fields[k] = v
    })
    const body = {
      engagement_id: e.id,
      broker_account_id: broker ? broker.id : null,
      bol: this.data.bol.trim(),
      issue_type: issue ? issue.slug : null,
      wechat_text: (this.data.note || '').trim(),
      fields
    }
    this.setData({ busy: true, err: '' })
    request('POST', '/cases', body)
      .then(() => wx.reLaunch({ url: '/pages/cases/index' }))
      .catch(() => this.setData({ busy: false, err: '提交失败，请检查填写' }))
  }
})
