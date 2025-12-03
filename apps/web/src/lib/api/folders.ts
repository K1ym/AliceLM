/**
 * 文件夹 API
 */

import { client } from "./client"
import type { Folder } from "./types"

export const foldersApi = {
  list: () => client.get<Folder[]>("/folders"),
  
  add: (folder_id: string, folder_type: string, import_existing: boolean = true) =>
    client.post("/folders", { folder_id, folder_type, import_existing }),
  
  delete: (id: number) => client.delete(`/folders/${id}`),
  
  scan: (id: number) => client.post(`/folders/${id}/scan`),
  
  toggle: (id: number) => client.patch(`/folders/${id}/toggle`),
}
