import ast

REPLACEMENTS={
 'TerraScope 回答更准，但直接改成像元计算并非总有效':'100 题对照：TerraScope 与掩膜核算',
 '为什么不能直接替换答案？':'掩膜核算带来的变化',
 '边界策略 MAE 为 5.02，高于提示词分歧的 4.68；没有全面领先。':'边界策略 MAE：5.02；提示词分歧 MAE：4.68',
 '不能直接替代专业解译\n几何计算也无法补回漏分的水体':'分割质量影响后续核算\n漏分水体需要进一步复核',
 '远离虚线的点是大误差。\n16 幅预算无法覆盖所有风险，\n同样需要检查未被标记的失败。':'远离虚线的点对应大误差。\n橙色样本进入本轮复核清单。',
 '完整标注子集中的解释性案例 · 均保留 RGB、预测掩膜和人工参考':'完整标注子集 · RGB、预测水体与人工标注对照',
 'India_747992 · 验证集真实样本 · 先由模型预测选入复核，再揭示人工参考':'India_747992 · 两种提示下的预测与人工标注对照',
 '保留 TerraScope 像素证据，把核查对象落到道路；每项输出都有可对照的标签':'TerraScope 水面提取、道路空间相交与核查清单',
 '同一批影像：整幅推理 → 四块局部放大 → 拼回原网格；没有训练模型，也没有新增观测信息':'同一批影像：整幅推理 → 四块局部放大 → 拼回原网格',
 '两种提示接近，不足以证明数值正确；额外光谱参照提供不同的信息':'两种提示下的水面变化与光谱参照比较',
 '可以讲的观察':'水面变化趋势',
 '需要保留的疑问':'不同方法的差异',
 '模型扩张幅度更大\n稳定预测也可能共同偏差':'模型估计的扩张幅度\n高于光谱参照',
 '仅作云干扰对照':'云干扰对照',
 '先于模型输出确定质量门槛':'影像质量筛选',
}

class Simplify(ast.NodeTransformer):
 def visit_Call(self,node):
  self.generic_visit(node)
  if isinstance(node.func,ast.Name) and node.func.id=='frame' and len(node.args)>=3:
   node.args[2]=ast.Constant('')
  return node
 def visit_Constant(self,node):
  if isinstance(node.value,str):
   node.value=REPLACEMENTS.get(node.value,node.value)
   node.value=node.value.replace('  ·  反映图中建筑周边受淹，不能据此估计室内损坏','')
  return node
 def visit_FunctionDef(self,node):
  self.generic_visit(node)
  if node.name=='save':
   args=[ast.Name(x.arg,ast.Load()) for x in node.args.args[:2]]
   node.body.insert(0,ast.Expr(ast.Call(ast.Name('classroom_polish',ast.Load()),args,[])))
  return node

def transform(code):
 code=code.replace('f"哈维飓风灾后影像 · 照片时间 {dt}（EXIF，时区未知） · 示例用于说明，整体结果见前页"', 'f"哈维飓风灾后航拍 · 拍摄日期 {dt[:10].replace(chr(58), chr(45))}"')
 tree=Simplify().visit(ast.parse(code));ast.fix_missing_locations(tree)
 return ast.unparse(tree)

def classroom_polish(fig,name):
 legend=None
 if name=='07_真实案例_核算有效与失效':legend='蓝色：预测水体    绿色：人工标注水体'
 elif name in ['12_真实案例_分歧触发复核','13_真实案例_低分歧仍会出错']:legend='灰色区域：无有效标注'
 elif '应用案例_' in name:legend='蓝色：模型水面    白线：道路轮廓    洋红：道路覆水    橙色：标注受淹建筑'
 elif name.startswith('18_'):legend='蓝色：两期均有水    橙色：新增候选    红色：减少候选    灰色：无效像元'
 elif name=='21_武汉_前期水面尺度检查':legend='蓝色：整幅推理水体    橙色：局部放大水体    灰色：无效像元'
 if legend:fig.text(.055,.055,legend,fontsize=14,color='#526678')
