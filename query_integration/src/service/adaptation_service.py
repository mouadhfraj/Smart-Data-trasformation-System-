import os
import re


class QueryAdapter:
    @staticmethod
    def adapt_references(query: str, project_dir: str) -> str:
        """
        Replace table references with proper dbt ref() calls
        Args:
            query: Raw SQL query string
            project_dir: Path to project directory
        Returns:
            Query with references adapted
        """
        models_path = os.path.join(project_dir, "models")
        if not os.path.exists(models_path):
            return query


        existing_models = {
            os.path.splitext(f)[0].lower(): os.path.splitext(f)[0]
            for f in os.listdir(models_path)
            if f.endswith('.sql')
        }


        table_ref_pattern = re.compile(
            r'(?i)(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+|$|;|\))'
        )

        def replace_match(match):
            prefix = match.group(1)
            table = match.group(2).lower()
            suffix = match.group(3)


            if table in existing_models:
                return f"{prefix} {{{{ ref('{existing_models[table]}') }}}}{suffix}"
            return match.group(0)


        return table_ref_pattern.sub(replace_match, query)