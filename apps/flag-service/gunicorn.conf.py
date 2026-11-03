def post_fork(server, worker):
    # Os workers são processos filhos; o SDK precisa iniciar dentro deles para
    # que o exportador de métricas continue ativo.
    from opentelemetry.instrumentation.auto_instrumentation import initialize

    initialize()
