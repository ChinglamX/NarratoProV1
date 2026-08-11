# Generated Contract Registry

本目录由 `make schemas` 生成，禁止手工编辑版本目录内容。

- `versions/<semver>/json-schema.json`：Draft 2020-12 公共 Contract Registry。
- `versions/<semver>/openapi.json`：OpenAPI 3.1 components 文档。
- `versions/<semver>/artifact-types.json`：Artifact Type/Domain/Owner Registry。
- `latest.json`：当前 Registry 版本指针。

历史版本目录不可覆盖或删除。兼容新增升级 minor/patch；破坏性变更必须升级 major，并提供迁移、ADR 和兼容验证。`make schema-check` 校验生成物与 Python Contract 源一致。
