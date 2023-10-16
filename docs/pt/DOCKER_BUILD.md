# Construção do Docker para Swirl Metasearch <img alt='Logotipo do Swirl Metasearch' src='https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl-logo-only-blue.png' width=38 align=left />

:warning: Aviso: ao usar o Docker, o banco de dados do Swirl é excluído instantaneamente e de forma irreversível quando o contêiner é desligado!

Entre em [contato com o suporte](#suporte) para obter uma imagem Docker adequada para implantação em produção.

<br/>

## Instalar o Docker

[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

<br/>

## Clonar o Branch do Repositório

```
git clone https://github.com/swirlai/swirl-search
```

Sinta-se à vontade para especificar o nome de um novo diretório, em vez de usar o padrão (`swirl-search`):

```
git clone https://github.com/swirlai/swirl-search meu-diretorio
```

<br/>

## Configurar o Contêiner

```
cd swirl-search
docker build . -t swirlai/swirl-search:latest
```

Se você clonou o repositório em um diretório diferente de `swirl-search`, substitua-o acima.

Este comando deve produzir uma longa resposta que começa com:

```
[+] Building 132.2s (21/21) FINISHED
...etc...
```

Se você vir mensagens de erro, entre em [contato com o suporte](#suporte) para obter ajuda.

<br/>

## Iniciar o Contêiner

```
docker compose up
```

O Docker deve responder com o seguinte, ou algo semelhante:

```
[+] Running 2/2
Network swirl-c_default Created 0.0s
Container swirl-c-app-1 Created 0.0s
Anexando ao swirl-search-app-1
```

### Anote o ID do contêiner anexado, pois ele será necessário posteriormente!

O ID do contêiner neste exemplo é `swirl-c-app-1`. Ele será diferente se você clonou o repositório em uma pasta diferente.

Pouco tempo depois, o Docker Desktop refletirá o contêiner em execução:

![Swirl em execução no Docker](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_docker.png)

<br/>

## Criar uma Conta de Super Usuário

```
docker exec -it swirl-search-app-1 python manage.py createsuperuser --email admin@example.com --username admin
```

Novamente, substitua `swirl-search-app-1` pelo ID do seu contêiner, se for diferente.

Digite uma nova senha, duas vezes. Se o Django reclamar que a senha é muito simples, digite "Y" para usá-la mesmo assim.

### Anote a senha do Super Usuário, pois ela será necessária posteriormente!

<br/>

## Carregar Provedores de Pesquisa do Google PSE

```
docker exec -it swirl-search-app-1 python swirl_load.py SearchProviders/google_pse.json -u admin -p super-user-password
```

Substitua `super-user-password` pela senha que você criou na etapa anterior. Além disso, substitua `swirl-search-app-1` pelo ID do seu contêiner, se for diferente.

O script carregará todas as configurações de Provedores de Pesquisa especificadas no arquivo de uma só vez e confirmará.

<br/>

## Visualizar Provedores de Pesquisa

### [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/)

Isso deve exibir o seguinte, ou algo semelhante:

![Provedores de Pesquisa do Swirl, Google PSE - 1](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_sp_pse-1.png)
![Provedores de Pesquisa do Swirl, Google PSE - 2](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_sp_pse-2.png)

<br/>

## Executar uma Consulta!

### [http://localhost:8000/swirl/search/?q=knowledge+management](http://localhost:8000/swirl/search/?q=knowledge+management)

Após 5-7 segundos, isso deve exibir uma lista unificada de resultados classificados por relevância:

![Resultados de Pesquisa do Swirl, Google PSE](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_results_mixed_1.png)

### Parabéns, o Swirl Docker está instalado!

<br/>

## Notas

:warning: Aviso: ao usar o Docker, o banco de dados do Swirl é excluído instantaneamente e de forma irreversível quando o contêiner é desligado!

Entre em [contato com o suporte](#suporte) para obter uma imagem Docker adequada para implantação em produção.

**Importante: o Swirl no Docker não pode usar localhost para se conectar a pontos de extremidade locais!**

Por exemplo: se você tem o Solr em execução em localhost:8983, o Swirl não poderá se conectar a partir do contêiner Docker usando essa URL.

Para configurar uma fonte desse tipo, obtenha o nome do host. No macOS:

```
% hostname
AgentCooper.local
```

Na configuração do Provedor de Pesquisa, substitua localhost pelo nome do host:

```
"url": "http://AgentCooper.local:8983/solr/{collection}/select?wt=json",
```

<br/>

## Documentação

* [Guia de Início Rápido](https://github.com/swirlai/swirl-search/wiki/1.-Quick-Start)
* [Guia do Usuário](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide)
* [Guia do Administrador](https://github.com/swirlai/swirl-search/wiki/3.-Admin-Guide)
* [Guia M365](https://github.com/swirlai/swirl-search/wiki/4.-M365-Guide)
* [Guia do Desenvolvedor](https://github.com/swirlai/swirl-search/wiki/5.-Developer-Guide)
* [Referência do Desenvolvedor](https://github.com/swirlai/swirl-search/wiki/6.-Developer-Reference)

<br/>

# Suporte

:small_blue_diamond: [Junte-se ao canal de suporte do Swirl SEARCH no Slack!](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

:small_blue_diamond: Email: [support@swirl.today](mailto:support@swirl.today) com problemas, solicitações, perguntas, etc. - adoraríamos ouvir você!
