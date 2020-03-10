# FATE-tools

开发的一个自用小工具 辅助联邦学习FATE框架的开发/测试, 目前能

1. 根据参数模板批量生成不同参数的conf,并自动提交任务, 检查任务状态, 这个功能对批量测试有用

2. 一键自动上传文件夹下所有.csv文件(文件夹下只能有csv), 并自动检测, 不会重复上传

3. 指定metric list从 all_component_metric里拿validate metric 并整理成csv

无命令行参数
