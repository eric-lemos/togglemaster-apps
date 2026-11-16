# auth-service (Go)

Este é o serviço de autenticação do projeto ToggleMaster. Ele é responsável por
criar e validar chaves de API.

## 📦 Pré-requisitos (Local)

* [Go](https://go.dev/doc/install) (versão 1.26 ou superior)
* [PostgreSQL](https://www.postgresql.org/download/) (rodando localmente ou em um
  contêiner Docker)

## 🚀 Rodando Localmente

1. **Clone o repositório** e entre na pasta `apps/auth-service`.

2. **Prepare o Banco de Dados:**
    * Crie um banco de dados no seu PostgreSQL (ex: `auth_db`).
    * Execute o script `db/init.sql` para criar a tabela `api_keys`:

        ```bash
        psql -U seu_usuario -d auth_db -f db/init.sql
        ```

3. **Configure as Variáveis de Ambiente:**
    O serviço lê diretamente as variáveis do ambiente; ele não carrega `.env`.
    No Bash, configure-as antes de iniciar:

    ```bash
    # String de conexão do seu banco de dados PostgreSQL
    export DATABASE_URL="postgres://SEU_USUARIO:SUA_SENHA@localhost:5432/auth_db"
    
    # Porta que o serviço irá rodar
    export PORT="8001"
    
    # Chave mestra para criar novas chaves de API
    export MASTER_KEY="admin-secreto-123"
    ```

4. **Instale as Dependências:**

    ```bash
    go mod download
    ```

5. **Inicie o Serviço:**

    ```bash
    go run .
    ```

    O servidor estará rodando em `http://localhost:8001`.

## 🧪 Testando os Endpoints

Você pode usar `curl` ou Postman.

**1. Verifique a Saúde (Health Check):**

```bash
curl http://localhost:8001/health
```

Saída esperada: `{"status":"ok"}`

**2. Crie uma nova Chave de API (requer a MASTER_KEY):**

```bash
curl -X POST http://localhost:8001/admin/keys \
-H "Content-Type: application/json" \
-H "Authorization: Bearer admin-secreto-123" \
-d '{"name": "meu-primeiro-servico"}'
```

Saída esperada (A SUA CHAVE SERÁ DIFERENTE):

```json
{
  "name": "meu-primeiro-servico",
  "key": "tm_key_a1b2c3d4...",
  "message": "Guarde esta chave com segurança! Você não poderá vê-la novamente."
}
```

**3. Valide a Chave que você acabou de criar:**

Substitua `tm_key_...` pela chave exata que você recebeu no passo anterior.

```bash
curl http://localhost:8001/validate \
-H "Authorization: Bearer tm_key_a1b2c3d4..."
```

Saída esperada: `{"message":"Chave válida"}`

**4. Teste uma Chave Inválida:**

```bash
curl http://localhost:8001/validate \
-H "Authorization: Bearer chave-errada-123"
```

Saída esperada: `Chave de API inválida ou inativa`
