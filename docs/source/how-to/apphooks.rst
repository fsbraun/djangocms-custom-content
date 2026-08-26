Expose content at a URL (app hooks)
===================================

Setting ``apphook = True`` on a content model's ``CMSConfig`` generates a CMS app
hook with a ready-made detail view. This page documents exactly what gets
generated, the URL it produces, and the contract your template must follow.

Enabling the app hook
---------------------

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        slug = models.SlugField()
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            apphook = True

Then attach it to a page: in the CMS page admin, open **Advanced settings** and
select the app hook (named after the grouper, e.g. *"Article"*), and publish.

What gets generated
-------------------

- **A detail view** — a Django ``DetailView`` over the *content* model.
- **No list view.** The app hook's root URL keeps serving the CMS page you
  attached it to, so that page owns its own index — usually a list plugin. This
  is a default, not a limitation: ``AppHookConfig(list_view=...)`` adds one. See
  :ref:`apphook-root-page`.
- **The URL** is ``<slug>/`` when the content model has a ``slug`` field, and
  ``<pk>/`` otherwise. Its route name is ``detail`` within an application
  namespace named after the grouper, lowercased (e.g. ``article``).
- **A** ``get_absolute_url()`` **method is injected onto the content model** (unless
  it already defines one). Prefer it over hand-writing ``{% url %}`` tags:

  .. code-block:: django

      <a href="{{ articlecontent.get_absolute_url }}">{{ articlecontent.title }}</a>

  The equivalent explicit reversal is ``{% url 'article:detail' slug=obj.slug %}``.

.. note::

   ``slug`` and ``language`` are read by the framework and carry rules of their
   own — in particular a versioned ``slug`` must **not** be ``unique=True``, and
   a ``language`` field makes the detail view resolve per language. See
   :ref:`special-fields`.

.. _apphook-root-page:

The root page is yours: listing content
---------------------------------------

Nothing is hard-wired to the app hook's root URL. **The CMS page owns it**, and
by default it goes on serving that page exactly as it did before the app hook was
attached.

That is deliberate. Generating a view for the root would quietly take the page
away from your editors: the index would come from a template inside the package,
and adding an introduction, a hero image or a call to action above the list would
mean overriding that template in code. Leaving the page in charge means the index
is built the same way as every other page on the site — out of plugins.

Two consequences worth being explicit about:

- **The default is no view, not "no index".** The index is a plugin on the page.
- **The default is overridable.** If a view really is the right answer,
  ``AppHookConfig(list_view=...)`` puts one at the root instead — see
  `Adding a list view after all`_.

Instead, leave the root serving the CMS page and put a **list plugin** on it. The
page keeps every placeholder it had, so an editor can arrange the index like any
other page:

.. code-block:: text

    /articles/                 <- the CMS page, with your plugins:
                                    Text plugin  "Everything we have written"
                                    Article list  (10 per page)
    /articles/hello-world/     <- the generated detail view

Writing the list plugin
~~~~~~~~~~~~~~~~~~~~~~~

The framework ships no list plugin of its own: a plugin needs a concrete model
and therefore a migration, and what to list — which filters, which ordering, what
an entry looks like — is an application decision. It is a dozen lines in your own
app, and ``contrib.blog`` carries a complete worked example including pagination
(``BlogPostList`` and ``BlogPostListPlugin``).

The shape:

.. code-block:: python

    class ArticleList(CMSPlugin):
        page_size = models.PositiveIntegerField(_("Articles per page"), default=10)

        @property
        def page_kwarg(self):
            # Namespaced by pk, so two lists on one page paginate independently.
            return f"page-{self.pk}" if self.pk else "page"

        def get_queryset(self):
            # ``objects`` is published-only once versioning is enabled.
            return ArticleContent.objects.all()


    @plugin_pool.register_plugin
    class ArticleListPlugin(CMSPluginBase):
        model = ArticleList
        render_template = "myapp/article_list.html"
        cache = False   # output depends on the page query parameter

        def render(self, context, instance, placeholder):
            context = super().render(context, instance, placeholder)
            paginator = Paginator(instance.get_queryset(), instance.page_size)
            request = context.get("request")
            page_number = request.GET.get(instance.page_kwarg) if request else None
            context["page_obj"] = paginator.get_page(page_number)
            context["posts"] = context["page_obj"].object_list
            return context

Three details worth copying from the blog example:

**Turn caching off.** A paginated plugin's output depends on the query string.
Leaving ``cache = True`` pins every visitor to page one.

**Namespace the page parameter.** Two list plugins on one page both reading
``?page=`` would move together. Keying it to the plugin's primary key
(``page-12``) keeps them independent.

**Do not 404 from inside a plugin.** An out-of-range page number should fall back
to the last page — the plugin is one element on somebody's page, and taking the
whole page down over it is disproportionate. ``Paginator.get_page()`` already
does this for junk input; the blog example also clamps out-of-range numbers.

.. tip::

   Such a plugin is not tied to the app hook. Put it on any page — a *Latest
   articles* block on the home page is the same plugin with a small page size.

Adding a list view after all
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some indexes are not editorial: a filtered feed, a search result, anything whose
shape comes from the query string rather than from what an editor arranged. Pass
a view class and it takes the root URL, under the route name ``list``:

.. code-block:: python

    class CMSConfig:
        apphook = AppHookConfig(list_view=ArticleListView)

The CMS page at that URL is then no longer rendered — the view answers instead —
so its placeholders become unreachable. That is the trade being made, and it is
why it is opt-in.

Customising what is generated
-----------------------------

``apphook = True`` is shorthand for a default
:class:`~djangocms_custom_content.apphooks.AppHookConfig`. Pass one to change what
is generated:

.. code-block:: python

    from django.urls import path
    from djangocms_custom_content.apphooks import AppHookConfig

    class ArticleContent(AbstractCustomContent):
        class CMSConfig:
            apphook = AppHookConfig(
                detail_view=ArticleDetailView,
                extra_urls=[
                    path("archive/<int:year>/", ArchiveView.as_view(), name="archive"),
                ],
            )

.. list-table::
   :widths: 22 78
   :header-rows: 1

   * - Argument
     - Effect
   * - ``detail_view``
     - View **class** for a single object. Defaults to the generated
       ``DetailView``. Subclass that (via
       ``custom_detail_view_factory``) to keep the language filtering and
       duplicate-slug handling.
   * - ``list_view``
     - View class for the app hook root. Defaults to ``None`` — see
       :ref:`apphook-root-page`.
   * - ``extra_urls``
     - Extra patterns, registered **before** the detail route so a literal path
       such as ``archive/`` wins over ``<slug:slug>/``.
   * - ``slug_field``
     - Field the detail URL routes on, and the name of the URL parameter.
       Defaults to ``slug`` when the model has one, otherwise the primary key.
       A custom value is passed on to the detail view as ``slug_field`` and
       ``slug_url_kwarg``, so a view you supply yourself has to accept those —
       any ``DetailView`` does. Naming a field the content model does not have
       raises ``ImproperlyConfigured`` at startup rather than failing on every
       request.
   * - ``namespace_field``
     - Field on the **grouper** naming the app hook instance an object belongs
       to. See `More than one app hook page`_.
   * - ``app_name``
     - Application namespace. Defaults to the grouper model name, lowercased.
   * - ``name``
     - Name shown in the page's *Application* dropdown.

More than one app hook page
---------------------------

django CMS registers one URL resolver per app hook *page*. Attach the same app
hook to ``/team/`` and ``/board/`` and both serve correctly — but reversing a URL
without saying which instance you mean always returns the first, so every link on
``/board/`` would point back at ``/team/``.

Tell the framework which instance an object belongs to by naming a field on the
grouper:

.. code-block:: python

    class Article(AbstractCustomGrouper):
        app_namespace = models.CharField(max_length=100, blank=True)

    class ArticleContent(AbstractCustomContent):
        class CMSConfig:
            apphook = AppHookConfig(namespace_field="app_namespace")

Set that field to the page's *Application instance name* (Advanced settings), and
``get_absolute_url()`` reverses with ``current_app``, landing on the right page.
An empty value falls back to the default instance.

Leave ``namespace_field`` unset and nothing changes — which is the right answer
for the single-page case.

The template contract
---------------------

Two render paths can use your template, and they expose the content object
**under its (lowercased) model name** — so use that variable for portability:

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Render path
     - Context variables
     - Template chosen
   * - App hook detail view
     - ``<modelname>`` **and** ``object``
     - ``<app_label>/<modelname>_detail.html``
   * - Frontend-editing render
     - ``<modelname>`` only
     - ``content.get_template()`` (same default)

For ``ArticleContent`` in app ``my_content`` that means the variable
``articlecontent`` and the template
``my_content/templates/my_content/articlecontent_detail.html``:

.. code-block:: django

    {% extends "base.html" %}
    {% load cms_tags %}

    {% block content %}
        {% cms_edit_on %}
        <article>
            <h1>{{ articlecontent.title }}</h1>
            <div>{{ articlecontent.body|safe }}</div>
        </article>
        {% cms_edit_off %}
    {% endblock %}

.. note::

   Use ``articlecontent``, **not** ``object`` — ``object`` is only present on the
   app-hook detail view, so a template that relies on it renders blank during
   frontend editing.

Overriding the template name
----------------------------

``AbstractCustomContent.get_template()`` returns
``<app_label>/<modelname>_detail.html`` by default. Overriding it changes the
template used by the **frontend-editing** render only; the app-hook detail view
still resolves its template from the model's ``template_name_suffix``
(``_detail``). To keep both paths on one template, override ``get_template`` *and*
name the file to match, or simply use the default convention.

See Also
--------

- :doc:`../tutorials/article_with_plugins` - App hook in a worked example
- :doc:`admin` - Editing the content behind these URLs
