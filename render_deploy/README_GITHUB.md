# 林国101角色海选 - 实时销量监控

实时监控微店商品销量，自动抓取库存数据并计算销量排名。

## 功能特性

- 📊 **实时销量监控** - 每5分钟自动抓取数据
- 🏆 **销量排名** - 18个角色实时排名
- 📱 **响应式设计** - 完美支持手机和电脑
- 🔄 **自动刷新** - 无需手动操作

## API 接口

| 接口 | 描述 |
|------|------|
| `GET /api/current` | 获取当前销量数据 |
| `GET /api/status` | 获取系统状态 |
| `GET /api/history?hours=24` | 获取历史数据 |

## 部署

本项目已配置 Render Blueprint，点击即可部署：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## 技术栈

- **后端**: Python + Flask
- **数据库**: SQLite
- **前端**: HTML + JavaScript
- **部署**: Render

## 数据说明

- 初始库存: 25000
- 销量 = 25000 - 当前库存
- 数据每5分钟更新一次

## License

MIT
