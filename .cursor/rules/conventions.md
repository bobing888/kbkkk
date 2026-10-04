# kbkkk 代码规范

## Conventional Commits

```
feat(scope): 新功能
fix(scope): bug 修复
docs(scope): 文档
refactor(scope): 重构
test(scope): 测试
chore(scope): 杂项
```

## PR 规则

- base 总是 main
- title 跟 commit message 一致（squash 合并会用 title）
- body 至少含：what / why / 不变量
- 单 PR 不超过 500 行（拆分参考）

## 文件命名

- Python: `snake_case.py`
- TS/JS: `camelCase.ts` / `PascalCase.tsx`
- MD: 标题用 `## 标题` 二级起
