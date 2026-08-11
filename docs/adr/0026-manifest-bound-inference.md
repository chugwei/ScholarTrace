# ADR 0026：推理必须先验证交付清单，再调用可替换 Provider

- 状态：accepted
- 日期：2026-08-11
- 范围：M12.2 推理接口

## 决策

`InferenceService` 接受一个交付根目录、`DeliveryManifest` 和可替换 `Predictor`。请求只能引用 Manifest 中登记的相对输入路径，并同时通过交付树文件哈希、请求输入哈希和模型版本校验；校验失败时不调用 Provider。默认 `FixturePredictor` 只用于离线/合成 smoke，输出和响应都保留证据等级与警告。

接口同时提供 `scholartrace infer` CLI 和可选的 `POST /api/inference`。没有配置交付 Manifest 的 API 返回 503，不能悄悄加载当前目录或任意模型；配置错误、哈希不符和版本冲突返回明确的 422。

## 理由

推理服务是交付包的边界，不能把“文件存在”当作模型版本正确，也不能把 Fixture 预测写成田间结论。先验证 Manifest 再调用 Provider，让未来真实模型、Docker 和 Staging 复用同一 provenance 门禁。

## 后续影响

M12.3 的 Compose 服务必须显式挂载交付根目录和 Manifest；生产 Provider 需要独立实现并提供真实模型哈希，不能替换离线 Fixture 的证据标签。
