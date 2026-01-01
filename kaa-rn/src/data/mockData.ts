export const MODULES = [
  { id: 'shop', name: '商店', icon: 'store', enabled: true, hasSettings: false },
  { id: 'work', name: '工作', icon: 'briefcase', enabled: true, hasSettings: false },
  { id: 'contest', name: '竞赛', icon: 'trophy', enabled: false, hasSettings: false },
  { id: 'training', name: '培育', icon: 'sprout', enabled: false, hasSettings: true },
  { id: 'mission', name: '任务', icon: 'clipboard-check', enabled: true, hasSettings: true },
  { id: 'guild', name: '社团', icon: 'account-group', enabled: true, hasSettings: true },
  { id: 'activity', name: '活动', icon: 'party-popper', enabled: false, hasSettings: true },
  { id: 'gift', name: '礼物', icon: 'gift', enabled: true, hasSettings: true },
  { id: 'gacha', name: '扭蛋', icon: 'pokeball', enabled: true, hasSettings: true },
];

export const LOGS = [
  { id: 1, time: '10:15:32', level: 'INFO', message: '开始领取礼物...' },
  { id: 2, time: '10:15:35', level: 'SUCCESS', message: '礼物领取成功' },
  { id: 3, time: '10:16:01', level: 'INFO', message: '正在检查商店...' },
  { id: 4, time: '10:16:05', level: 'INFO', message: '商店无需购买' },
  { id: 5, time: '10:17:20', level: 'INFO', message: '开始工作任务...' },
  { id: 6, time: '10:17:45', level: 'SUCCESS', message: '工作任务完成' },
];

export const STATUS = {
  state: '运行中',
  detail: '正在领取礼物',
};
