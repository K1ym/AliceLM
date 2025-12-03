/**
 * API 模块
 * 
 * 此文件为向后兼容保留，推荐直接从 @/lib/api 导入
 * 实际实现已拆分到 lib/api/ 目录下
 */

// 重新导出所有内容
export * from "./api/index"

// 为了兼容旧代码，保留 api 和 default 导出
import { client } from "./api/client"
export const api = client
export default client
