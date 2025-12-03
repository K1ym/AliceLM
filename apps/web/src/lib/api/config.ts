/**
 * 配置 API
 */

import { client } from "./client"
import type {
  ASRConfig,
  LLMConfig,
  ConfigResponse,
  ASRProvidersResponse,
  LLMProvidersResponse,
  LLMEndpoint,
  LLMModel,
  ModelTaskConfig,
  ModelTasksConfig,
  PromptsResponse,
} from "./types"

export const configApi = {
  get: () => client.get<ConfigResponse>("/config"),
  
  updateASR: (config: ASRConfig) => 
    client.put("/config/asr", config),
  
  updateLLM: (config: LLMConfig) => 
    client.put("/config/llm", config),
  
  updateNotify: (config: { wechat_enabled: boolean; webhook_url?: string }) =>
    client.put("/config/notify", config),
  
  getASRProviders: () => 
    client.get<ASRProvidersResponse>("/config/asr/providers"),
  
  getLLMProviders: () => 
    client.get<LLMProvidersResponse>("/config/llm/providers"),
  
  fetchLLMModels: (base_url?: string, api_key?: string) => {
    const body: Record<string, string> = {}
    if (base_url) body.base_url = base_url
    if (api_key) body.api_key = api_key
    return client.post<{ models: LLMModel[] }>("/config/llm/models", body)
  },
  
  // LLM 端点管理
  createLLMEndpoint: (data: { name: string; base_url: string; api_key: string }) =>
    client.post<LLMEndpoint>("/config/llm/endpoints", data),
  
  deleteLLMEndpoint: (endpointId: string) =>
    client.delete(`/config/llm/endpoints/${endpointId}`),
  
  refreshEndpointModels: (endpointId: string) =>
    client.post<{ success: boolean; models: string[] }>(
      `/config/llm/endpoints/${endpointId}/refresh`
    ),
  
  // 任务模型配置
  updateModelTasks: (config: ModelTasksConfig) =>
    client.put("/config/model-tasks", config),
  
  updateSingleModelTask: (taskType: string, config: ModelTaskConfig) =>
    client.put(`/config/model-tasks/${taskType}`, config),
  
  // Prompt 配置
  getPrompts: () => client.get<PromptsResponse>("/config/prompts"),
  
  updatePrompt: (promptType: string, content: string) =>
    client.put(`/config/prompts/${promptType}`, { 
      prompt_type: promptType, 
      content 
    }),
  
  resetPrompt: (promptType: string) =>
    client.delete(`/config/prompts/${promptType}`),
}
