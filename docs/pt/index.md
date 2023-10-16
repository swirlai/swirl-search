# Documentação do Swirl

**Conteúdo**
* TOC
{:toc}

## O que é Metasearch? É o mesmo que Pesquisa Federada?

[Metasearch](https://en.wikipedia.org/wiki/Federated_search) é uma abordagem técnica na qual um mecanismo de pesquisa (ou "broker") aceita uma consulta de algum usuário (ou sistema), distribui a consulta para outros mecanismos de pesquisa, aguarda as respostas e depois retorna um conjunto de resultados normalizados, unificados e idealmente classificados por relevância.

![Diagrama de Metasearch](../images/swirl_arch_diagram.jpg)

A abordagem de metasearch difere dos mecanismos de pesquisa tradicionais [para empresas](https://en.wikipedia.org/wiki/Enterprise_search) que processam [cópias de todos os dados de origem](https://en.wikipedia.org/wiki/Extract,_transform,_load) e [indexam esses dados](https://en.wikipedia.org/wiki/Search_engine_indexing), o que pode ser caro e demorado.

O metasearch deixa os dados de origem no local e depende do mecanismo de pesquisa de cada fonte para obter acesso. Isso torna a pesquisa federada menos adequada para navegação profunda - em um grande catálogo de comércio eletrônico ou conjunto de dados, por exemplo - mas ideal para fornecer resultados interligados com uma fração do esforço. Também é excelente para enriquecimento de informações, análise de entidades (como inteligência competitiva, de clientes, de setor ou de mercado) e integração de dados não estruturados para curadoria de conteúdo, aplicativos de ciência de dados e aprendizado de máquina.

## O que é Swirl Metasearch?

[Swirl Metasearch](https://github.com/swirlai/swirl-search) é um mecanismo de pesquisa metasearch construído na pilha Python/Django e lançado sob a licença Apache 2.0 em 2022.

O Swirl inclui conectores para muitos sistemas populares, incluindo mecanismos de pesquisa, bancos de dados e outros serviços em nuvem corporativa - qualquer coisa com uma API de consulta.

![Fontes do Swirl](../images/swirl_source_no_m365-galaxy_dark.png)

Use as APIs do Swirl para executar pesquisas e acompanhar seu progresso em tempo real, em seguida, recupere resultados unificados reclassificados pelo modelo de similaridade de vetores de cosseno embutido no Swirl, com base no [spaCy](https://spacy.io), além de impulsionar termos e frases.

![Resultados do Swirl](../images/swirl_results_no_m365-galaxy_dark.png)

O Swirl fornece uma `swirl_score` e `swirl_rank` para cada item, além da classificação da fonte original, para que os usuários possam ver instantaneamente o que foi mais relevante em todas as fontes.

``` shell
 "results": [
        {
            "swirl_rank": 1,
            "swirl_score": 1020.4933333333332,
            "searchprovider": "Mecanismos de Pesquisa Empresarial - Google PSE",
            "searchprovider_rank": 1,
            "title": "Swirl <em>Metasearch</em>: Home",
            "url": "https://swirl.today/",
            "body": "Swirl <em>Metasearch</em> conecta silos de dados, retorna resultados classificados por IA para uma única experiência e simplifica implantações de pesquisa para aplicativos.",
            "date_published": "desconhecido",
            "date_published_display": "",
            "date_retrieved": "2023-07-10 17:19:00.331417",
            "author": "swirl.today",
           ...
            },
```

Os desenvolvedores de pesquisa podem renderizar os resultados JSON do Swirl em qualquer IU ou estrutura existente sem ter que normalizar os nomes dos campos. Cientistas de dados e engenheiros, gerentes de pesquisa, analistas e implementadores que trabalharam com Elastic ou Solr acharão fácil adicionar resultados de qualquer fonte com uma API de pesquisa típica à sua infraestrutura de pesquisa existente.

# Documentação

| [Início](index.md) | [Início Rápido](1.-Quick-Start.md) | [Guia do Usuário](2.-User-Guide.md) | [Guia do Administrador](3.-Admin-Guide.md) | [Guia M365](4.-M365-Guide.md) | [Guia do Desenvolvedor](5.-Developer-Guide.md) | [Referência do Desenvolvedor](6.-Developer-Reference.md) |

# Suporte

* [Junte-se à Comunidade do Swirl Metasearch no Slack!](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

* Email: [support@swirl.today](mailto:support@swirl.today) com problemas, solicitações, perguntas, etc. - adoraríamos ouvir você!