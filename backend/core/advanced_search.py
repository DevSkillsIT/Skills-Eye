"""
Advanced Metadata Search
Provides powerful search capabilities with operators, regex, and complex queries.
"""
import re
from typing import Any, Dict, List, Optional, Set
from enum import Enum


class SearchOperator(str, Enum):
    """Search operators for metadata filtering"""
    EQUALS = "eq"           # Exact match
    NOT_EQUALS = "ne"       # Not equal
    CONTAINS = "contains"   # String contains
    REGEX = "regex"         # Regular expression
    IN = "in"              # Value in list
    NOT_IN = "not_in"      # Value not in list
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GT = "gt"              # Greater than (numeric)
    LT = "lt"              # Less than (numeric)
    GTE = "gte"            # Greater than or equal
    LTE = "lte"            # Less than or equal


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions"""
    AND = "and"
    OR = "or"


class SearchCondition:
    """Represents a single search condition"""

    def __init__(
        self,
        field: str,
        operator: SearchOperator,
        value: Any
    ):
        self.field = field
        self.operator = SearchOperator(operator)
        self.value = value

    def matches(self, item: Dict[str, Any]) -> bool:
        """
        Check if an item matches this condition.

        Args:
            item: Dictionary to check (service data with Meta field)

        Returns:
            True if matches, False otherwise
        """
        # Get value from item (support nested paths like "Meta.company")
        item_value = self._get_nested_value(item, self.field)

        if item_value is None and self.operator not in [SearchOperator.NOT_EQUALS, SearchOperator.NOT_IN]:
            return False

        # Apply operator
        if self.operator == SearchOperator.EQUALS:
            return str(item_value) == str(self.value)

        elif self.operator == SearchOperator.NOT_EQUALS:
            return str(item_value) != str(self.value)

        elif self.operator == SearchOperator.CONTAINS:
            return str(self.value).lower() in str(item_value).lower()

        elif self.operator == SearchOperator.REGEX:
            try:
                pattern = re.compile(str(self.value), re.IGNORECASE)
                return bool(pattern.search(str(item_value)))
            except re.error:
                return False

        elif self.operator == SearchOperator.IN:
            if not isinstance(self.value, list):
                return False
            return item_value in self.value

        elif self.operator == SearchOperator.NOT_IN:
            if not isinstance(self.value, list):
                return True
            return item_value not in self.value

        elif self.operator == SearchOperator.STARTS_WITH:
            return str(item_value).lower().startswith(str(self.value).lower())

        elif self.operator == SearchOperator.ENDS_WITH:
            return str(item_value).lower().endswith(str(self.value).lower())

        elif self.operator in [SearchOperator.GT, SearchOperator.LT, SearchOperator.GTE, SearchOperator.LTE]:
            try:
                item_num = float(item_value)
                value_num = float(self.value)

                if self.operator == SearchOperator.GT:
                    return item_num > value_num
                elif self.operator == SearchOperator.LT:
                    return item_num < value_num
                elif self.operator == SearchOperator.GTE:
                    return item_num >= value_num
                elif self.operator == SearchOperator.LTE:
                    return item_num <= value_num
            except (ValueError, TypeError):
                return False

        return False

    def _get_nested_value(self, item: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Examples:
            "Meta.company" -> item["Meta"]["company"]
            "tags" -> item["tags"]
        """
        keys = path.split(".")
        value = item

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value


class SearchQuery:
    """Represents a complex search query with multiple conditions"""

    def __init__(
        self,
        conditions: List[SearchCondition],
        logical_operator: LogicalOperator = LogicalOperator.AND
    ):
        self.conditions = conditions
        self.logical_operator = LogicalOperator(logical_operator)

    def matches(self, item: Dict[str, Any]) -> bool:
        """
        Check if an item matches this query.

        Args:
            item: Dictionary to check

        Returns:
            True if matches, False otherwise
        """
        if not self.conditions:
            return True

        results = [condition.matches(item) for condition in self.conditions]

        if self.logical_operator == LogicalOperator.AND:
            return all(results)
        else:  # OR
            return any(results)


class AdvancedSearch:
    """Advanced search engine for Consul services and metadata"""

    @staticmethod
    def search(
        items: List[Dict[str, Any]],
        conditions: List[Dict[str, Any]],
        logical_operator: str = "and"
    ) -> List[Dict[str, Any]]:
        """
        Search items with advanced conditions.

        Args:
            items: List of items to search
            conditions: List of condition dictionaries, each with:
                - field: Field path (e.g., "Meta.company", "tags")
                - operator: Operator (eq, contains, regex, etc.)
                - value: Value to compare
            logical_operator: How to combine conditions (and/or)

        Returns:
            Filtered list of items

        Example:
            conditions = [
                {"field": "Meta.company", "operator": "eq", "value": "Ramada"},
                {"field": "Meta.env", "operator": "in", "value": ["prod", "staging"]}
            ]
            results = AdvancedSearch.search(services, conditions, "and")
        """
        # Convert dictionaries to SearchCondition objects
        search_conditions = [
            SearchCondition(
                field=c["field"],
                operator=c["operator"],
                value=c["value"]
            )
            for c in conditions
        ]

        # Create query
        query = SearchQuery(search_conditions, logical_operator)

        # Filter items
        return [item for item in items if query.matches(item)]

    @staticmethod
    def extract_unique_values(
        items: List[Dict[str, Any]],
        field: str
    ) -> List[str]:
        """
        Extract unique values for a field across all items.

        Args:
            items: List of items
            field: Field path (e.g., "Meta.company")

        Returns:
            Sorted list of unique values
        """
        values: Set[str] = set()

        for item in items:
            condition = SearchCondition(field, SearchOperator.EQUALS, None)
            value = condition._get_nested_value(item, field)

            if value is not None:
                if isinstance(value, list):
                    values.update(str(v) for v in value)
                else:
                    values.add(str(value))

        return sorted(values)

    @staticmethod
    def build_filters_from_metadata(items: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build filter options from metadata.

        Returns dictionary with available values for common fields.

        Args:
            items: List of items to analyze

        Returns:
            Dictionary mapping field names to lists of unique values
        """
        common_fields = [
            "Meta.module",
            "Meta.company",
            "Meta.project",
            "Meta.env",
            "Meta.datacenter",
            "service",
            "tags"
        ]

        filters = {}

        for field in common_fields:
            values = AdvancedSearch.extract_unique_values(items, field)
            if values:
                # Clean field name for output
                field_name = field.split(".")[-1]
                filters[field_name] = values

        return filters

    @staticmethod
    def search_text(
        items: List[Dict[str, Any]],
        text: str,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across multiple fields.

        Args:
            items: List of items to search
            text: Text to search for
            fields: Optional list of fields to search (default: all common fields)

        Returns:
            Items matching the text in any of the specified fields
        """
        if not text:
            return items

        if fields is None:
            fields = [
                "Meta.name",
                "Meta.instance",
                "Meta.company",
                "Meta.project",
                "service",
                "id"
            ]

        # Create OR condition for all fields
        conditions = [
            SearchCondition(field, SearchOperator.CONTAINS, text)
            for field in fields
        ]

        query = SearchQuery(conditions, LogicalOperator.OR)

        return [item for item in items if query.matches(item)]

    @staticmethod
    def sort_by_field(
        items: List[Dict[str, Any]],
        field: str,
        descending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sort items by a field.

        Args:
            items: List of items to sort
            field: Field path to sort by
            descending: Sort in descending order

        Returns:
            Sorted list
        """
        def get_sort_key(item: Dict[str, Any]) -> Any:
            condition = SearchCondition(field, SearchOperator.EQUALS, None)
            value = condition._get_nested_value(item, field)
            return value if value is not None else ""

        return sorted(items, key=get_sort_key, reverse=descending)

    @staticmethod
    def paginate(
        items: List[Dict[str, Any]],
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Paginate results.

        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dictionary with paginated data and metadata
        """
        total = len(items)
        total_pages = (total + page_size - 1) // page_size  # Ceiling division

        # Ensure page is valid
        page = max(1, min(page, total_pages if total_pages > 0 else 1))

        # Calculate slice indices
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "data": items[start:end],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        }
