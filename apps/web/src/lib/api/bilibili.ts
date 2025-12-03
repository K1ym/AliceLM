/**
 * B站 API
 */

import { client } from "./client"
import type {
  BilibiliQRCode,
  BilibiliQRCodeStatus,
  BilibiliBindStatus,
  BilibiliFoldersResponse,
  BilibiliFolderDetailResponse,
} from "./types"

export const bilibiliApi = {
  getQRCode: () => client.get<BilibiliQRCode>("/bilibili/qrcode"),
  
  pollQRCode: (qrcode_key: string) =>
    client.get<BilibiliQRCodeStatus>("/bilibili/qrcode/poll", { 
      params: { qrcode_key } 
    }),
  
  getStatus: () => client.get<BilibiliBindStatus>("/bilibili/status"),
  
  unbind: () => client.delete("/bilibili/unbind"),
  
  getFolders: () => client.get<BilibiliFoldersResponse>("/bilibili/folders"),
  
  getFolderVideos: (folderType: string, folderId: string) =>
    client.get<BilibiliFolderDetailResponse>(
      `/bilibili/folders/${folderType}/${folderId}`
    ),
}
