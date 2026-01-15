"""
CalloutList rule - Callouts are not supported in DITA.

Source: https://github.com/jhradilek/asciidoctor-dita-vale
"""

from .base import Rule, RuleSeverity, RuleExample

CALLOUT_LIST = Rule(
    name="CalloutList",
    severity=RuleSeverity.WARNING,
    message="Callouts are not supported in DITA.",
    link="https://github.com/jhradilek/asciidoctor-dita-vale/blob/main/README.md#warnings",
    fix_instruction="""DITA 1.3 does not support callout markers (<1>, <2>, etc.) in code blocks.

TO FIX:
1. Remove callout markers from inside code blocks
2. Replace the callout list with a description list below the code block
3. Reference the code by quoting the relevant line or variable name

The callouts-conversion tool can help automate this process.

FORMAT FOR DESCRIPTION LIST:
term:: definition
another term:: another definition""",
    examples=[
        RuleExample(
            description="Convert callouts to description list",
            before="""[source,yaml]
----
apiVersion: v1 # <1>
kind: Pod # <2>
metadata:
  name: my-pod # <3>
----
<1> API version
<2> Resource type
<3> Pod name""",
            after="""[source,yaml]
----
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
----

apiVersion: v1:: API version
kind: Pod:: Resource type
name: my-pod:: Pod name""",
        ),
    ],
)
