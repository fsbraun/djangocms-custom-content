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
- **The URL** is ``<slug>/`` when the content model has a ``slug`` field, and
  ``<pk>/`` otherwise. Its route name is ``detail`` within an application
  namespace named after the grouper, lowercased (e.g. ``article``).
- **A** ``get_absolute_url()`` **method is injected onto the content model** (unless
  it already defines one). Prefer it over hand-writing ``{% url %}`` tags:

  .. code-block:: django

      <a href="{{ articlecontent.get_absolute_url }}">{{ articlecontent.title }}</a>

  The equivalent explicit reversal is ``{% url 'article:detail' slug=obj.slug %}``.

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
