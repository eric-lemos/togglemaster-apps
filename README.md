# ToggleMaster Apps

Este repositório contém os microsserviços da plataforma ToggleMaster, um sistema de *feature flags*. As aplicações permitem cadastrar flags, definir regras de segmentação, consultar a decisão para um usuário e armazenar eventos de avaliação para análise.

## Arquitetura

```mermaid
flowchart LR
    Client[Aplicação cliente] -->|GET /evaluate| Eval[evaluation-service]
    Eval -->|cache, TTL 30 s| Redis[(Redis)]
    Eval -->|flag| Flags[flag-service]
    Eval -->|regra| Targeting[targeting-service]
    Flags --> Auth[auth-service]
    Targeting --> Auth
    Auth --> AuthDB[(PostgreSQL: auth)]
    Flags --> FlagDB[(PostgreSQL: flags)]
    Targeting --> TargetDB[(PostgreSQL: targeting)]
    Eval -->|eventos de avaliação| SQS[[AWS SQS]]
    SQS --> Analytics[analytics-service]
    Analytics --> Dynamo[(AWS DynamoDB)]
```

O `evaluation-service` é o endpoint de consulta usado pelas aplicações cliente. O Redis guarda por 30 segundos os dados de flag e regra; em caso de cache miss, o serviço consulta `flag-service` e `targeting-service`. A decisão é determinística para cada combinação de usuário e flag.

O `auth-service` cria chaves de API e valida as chaves usadas pelos serviços administrativos. O `evaluation-service` usa uma chave de serviço para consultar os outros dois serviços. Os eventos de avaliação são enviados ao SQS de forma assíncrona; o `analytics-service` consome a fila e grava os eventos no DynamoDB.

## Serviços

| Serviço | Porta padrão | Responsabilidade |
|---|---:|---|
| `auth-service` | 8001 | Criação e validação de chaves de API |
| `flag-service` | 8002 | CRUD das definições de feature flags |
| `targeting-service` | 8003 | CRUD das regras de segmentação |
| `evaluation-service` | 8004 | Avaliação de flags com cache em Redis |
| `analytics-service` | 8005 | Worker de eventos SQS e gravação no DynamoDB; expõe apenas `/health` |

Cada serviço tem seu próprio `README.md` com informações específicas:

- [auth-service](apps/auth-service/README.md)
- [flag-service](apps/flag-service/README.md)
- [targeting-service](apps/targeting-service/README.md)
- [evaluation-service](apps/evaluation-service/README.md)
- [analytics-service](apps/analytics-service/README.md)

## Pré-requisitos

- Go 1.26 ou superior para os serviços Go (`go.mod`).
- Python 3.11 para os serviços Python (versão usada pelas imagens Docker).
- PostgreSQL para persistir chaves, flags e regras.
- Redis para o cache do `evaluation-service`.
- AWS SQS e DynamoDB, além de credenciais/permissões AWS, para o fluxo de analytics.
- `curl` para os exemplos abaixo.

Os três serviços que usam PostgreSQL podem usar instâncias diferentes ou a mesma instância com bancos separados. Crie os bancos `auth_db`, `flags_db` e `targeting_db` (ou ajuste os nomes nas respectivas URLs) e aplique os scripts de inicialização:

```bash
psql "$AUTH_DATABASE_URL" -f apps/auth-service/db/init.sql
psql "$FLAGS_DATABASE_URL" -f apps/flag-service/db/init.sql
psql "$TARGETING_DATABASE_URL" -f apps/targeting-service/db/init.sql
```

As variáveis acima são apenas exemplos para as URLs de conexão; defina cada uma no terminal antes de executar os comandos, ou substitua-as pelas URLs correspondentes.

## Configuração

Configure as variáveis de ambiente indicadas abaixo. Os serviços Python e o `evaluation-service` carregam um arquivo `.env` local na pasta do próprio serviço. O `auth-service` lê as variáveis diretamente do ambiente do processo; exporte-as no terminal ou configure-as no ambiente de execução.

| Serviço | Variáveis necessárias | Opcionais |
|---|---|---|
| `auth-service` | `DATABASE_URL`, `MASTER_KEY` | `PORT` (padrão `8001`) |
| `flag-service` | `DATABASE_URL`, `AUTH_SERVICE_URL` | `PORT` (padrão `8002`) |
| `targeting-service` | `DATABASE_URL`, `AUTH_SERVICE_URL` | `PORT` (padrão `8003`) |
| `evaluation-service` | `REDIS_URL`, `FLAG_SERVICE_URL`, `TARGETING_SERVICE_URL`, `SERVICE_API_KEY` | `PORT` (padrão `8004`), `AWS_SQS_URL`, `AWS_REGION`, `AWS_SQS_ENDPOINT` |
| `analytics-service` | `AWS_REGION`, `AWS_SQS_URL`, `AWS_DYNAMODB_TABLE` | `PORT` (padrão `8005`), `AWS_SQS_ENDPOINT` |

Exemplos de valores para execução local:

```dotenv
# auth-service
DATABASE_URL=postgres://usuario:senha@localhost:5432/auth_db
MASTER_KEY=defina-um-segredo-local-forte
PORT=8001

# flag-service
DATABASE_URL=postgres://usuario:senha@localhost:5432/flags_db
AUTH_SERVICE_URL=http://localhost:8001
PORT=8002

# targeting-service
DATABASE_URL=postgres://usuario:senha@localhost:5432/targeting_db
AUTH_SERVICE_URL=http://localhost:8001
PORT=8003

# evaluation-service
REDIS_URL=redis://localhost:6379
FLAG_SERVICE_URL=http://localhost:8002
TARGETING_SERVICE_URL=http://localhost:8003
SERVICE_API_KEY=chave-criada-no-auth-service
AWS_SQS_URL=https://sqs.us-east-1.amazonaws.com/123456789012/togglemaster-events
AWS_REGION=us-east-1

# analytics-service
AWS_SQS_URL=https://sqs.us-east-1.amazonaws.com/123456789012/togglemaster-events
AWS_REGION=us-east-1
AWS_DYNAMODB_TABLE=ToggleMasterAnalytics
```

Use URLs e credenciais próprias para o seu ambiente; não versione arquivos `.env` ou chaves reais. Para acessar a AWS, os SDKs usam a cadeia padrão de credenciais, como perfil local da AWS CLI ou variáveis de ambiente. `AWS_SQS_ENDPOINT` pode ser configurado para apontar a um endpoint compatível com SQS durante desenvolvimento local.

O DynamoDB deve ter uma tabela com o nome definido em `AWS_DYNAMODB_TABLE` e uma chave de partição `event_id` do tipo String. A fila SQS deve ser a mesma para o `evaluation-service` e o `analytics-service`. O primeiro precisa permissão para enviar mensagens; o segundo, para receber e excluir mensagens e gravar itens no DynamoDB.

`AWS_SQS_URL` é opcional no `evaluation-service`: sem ela, as avaliações continuam funcionando, mas os eventos não são enviados à AWS. Para o `analytics-service`, SQS, DynamoDB e credenciais AWS são necessários para iniciar o processo.

## Executar localmente

Inicie PostgreSQL e Redis, configure as variáveis de ambiente e aplique os scripts SQL indicados acima. Em seguida, abra um terminal para cada serviço. Execute-os nesta ordem para permitir que as dependências já estejam disponíveis:

```bash
# Terminal 1 — auth-service
cd apps/auth-service
go run .

# Terminal 2 — flag-service
cd apps/flag-service
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8002 app:app

# Terminal 3 — targeting-service
cd apps/targeting-service
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8003 app:app

# Terminal 4 — evaluation-service
cd apps/evaluation-service
go run .

# Terminal 5 — analytics-service (opcional para avaliar flags)
cd apps/analytics-service
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8005 app:app
```

Instale as dependências Python no diretório de cada serviço, preferencialmente em um ambiente virtual isolado. O `evaluation-service` carrega `.env`; o `auth-service` precisa receber `DATABASE_URL` e `MASTER_KEY` no ambiente antes de `go run .`.

## Fluxo de uso rápido

Os exemplos usam `Bearer` no cabeçalho `Authorization`. Defina primeiro `MASTER_KEY` com o mesmo valor configurado no `auth-service`.

1. Verifique os serviços:

   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   curl http://localhost:8004/health
   curl http://localhost:8005/health
   ```

2. Crie uma chave para o `evaluation-service`. A chave em texto puro é retornada somente nesta resposta; guarde-a com segurança e configure-a como `SERVICE_API_KEY`:

   ```bash
   curl -X POST http://localhost:8001/admin/keys \
     -H "Authorization: Bearer $MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"evaluation-service"}'
   ```

3. Use a chave criada para cadastrar uma flag e sua regra:

   ```bash
   curl -X POST http://localhost:8002/flags \
     -H "Authorization: Bearer $SERVICE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"enable-new-dashboard","description":"Novo dashboard","is_enabled":true}'

   curl -X POST http://localhost:8003/rules \
     -H "Authorization: Bearer $SERVICE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"flag_name":"enable-new-dashboard","is_enabled":true,"rules":{"type":"PERCENTAGE","value":50}}'
   ```

4. Consulte a decisão:

   ```bash
   curl "http://localhost:8004/evaluate?user_id=user-123&flag_name=enable-new-dashboard"
   ```

   A resposta tem o formato `{"flag_name":"enable-new-dashboard","user_id":"user-123","result":true}`. O resultado depende do usuário e do nome da flag e é estável para a mesma combinação enquanto a definição/regra não mudar.

## API

| Serviço | Método e rota | Autenticação | Descrição |
|---|---|---|---|
| `auth-service` | `GET /health` | Não | Verificação de saúde |
| `auth-service` | `POST /admin/keys` | `MASTER_KEY` como Bearer | Cria uma chave de API |
| `auth-service` | `GET /validate` | Chave de API como Bearer | Valida uma chave |
| `flag-service` | `GET /health` | Não | Verificação de saúde |
| `flag-service` | `POST /flags` | Chave de API | Cria uma flag |
| `flag-service` | `GET /flags` | Chave de API | Lista flags |
| `flag-service` | `GET /flags/{name}` | Chave de API | Consulta uma flag |
| `flag-service` | `PUT /flags/{name}` | Chave de API | Atualiza `description` e/ou `is_enabled` |
| `flag-service` | `DELETE /flags/{name}` | Chave de API | Exclui uma flag |
| `targeting-service` | `GET /health` | Não | Verificação de saúde |
| `targeting-service` | `POST /rules` | Chave de API | Cria uma regra |
| `targeting-service` | `GET /rules/{flag_name}` | Chave de API | Consulta uma regra |
| `targeting-service` | `PUT /rules/{flag_name}` | Chave de API | Atualiza `rules` e/ou `is_enabled` |
| `targeting-service` | `DELETE /rules/{flag_name}` | Chave de API | Exclui uma regra |
| `evaluation-service` | `GET /health` | Não | Verificação de saúde |
| `evaluation-service` | `GET /evaluate?user_id=...&flag_name=...` | Não | Retorna a decisão para usuário e flag |
| `analytics-service` | `GET /health` | Não | Verificação de saúde do processo |

As regras implementadas atualmente pelo `evaluation-service` são do tipo `PERCENTAGE`, com `value` numérico (use o intervalo percentual de 0 a 100; a API não valida esse limite). Uma flag desativada resulta em `false`; uma flag ativa sem regra de segmentação (ou com a regra desativada) resulta em `true`. Flag inexistente retorna `result: false`. A rota de avaliação retorna HTTP 400 quando faltam `user_id` ou `flag_name`.

Os endpoints `/health` confirmam que o processo HTTP está ativo, mas não garantem que banco de dados, Redis ou recursos AWS estejam acessíveis.

## Docker

Cada serviço tem um `Dockerfile` próprio. Para construir uma imagem, execute o comando a partir da pasta do serviço:

```bash
docker build -t togglemaster-auth .
```

Troque o nome da imagem conforme necessário. Configure as mesmas variáveis de ambiente no contêiner; as imagens não fornecem, por si só, PostgreSQL, Redis, SQS ou DynamoDB. As portas padrão das imagens são as listadas na tabela de serviços.
