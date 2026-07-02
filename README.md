# Menu Planner for Hermes 

Персональный планировщик меню на базе Hermes Agent. 

## Runtime model 

Hermes запускается из готового Docker-образа через Docker Compose. 

Проект не использует собственный Dockerfile для Hermes. 

Прикладные компоненты подключаются через bind mounts: 

- configuration; 
- Menu Planner Plugin; 
- Hermes skills; 
- application source code. 

Изменяемое состояние хранится в named volumes или внешней базе данных. 

Ручные изменения внутри работающего контейнера запрещены.

## Current stage 

Stage 0: environment setup and Hermes capability spike.