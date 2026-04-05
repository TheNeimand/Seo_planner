"""
Interactive graph visualization widget using QGraphicsScene/QGraphicsView.
Displays the site map as a force-directed graph with clickable nodes.
"""
import math
import logging
from typing import Optional

from PySide6.QtCore import (
    Qt, QRectF, QPointF, Signal, QPropertyAnimation,
    QEasingCurve, QTimer, Property,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QRadialGradient,
    QLinearGradient, QPainterPath, QWheelEvent, QMouseEvent,
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsDropShadowEffect, QGraphicsPathItem,
    QWidget, QVBoxLayout,
)

from src.config import NODE_COLORS, NODE_SIZES, COLORS
from src.gsc.models import Page

logger = logging.getLogger(__name__)


class NodeItem(QGraphicsEllipseItem):
    """
    A graph node representing a page.
    Supports hover effects, selection glow, and dragging.
    """

    def __init__(
        self,
        url: str,
        page: Page,
        x: float,
        y: float,
        radius: float,
        color: str,
        parent=None,
    ):
        self.radius = radius
        super().__init__(
            -radius, -radius, radius * 2, radius * 2, parent
        )
        self.url = url
        self.page = page
        self.base_color = QColor(color)
        self.hover_color = self.base_color.lighter(140)

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(10)

        # Visual setup
        self._setup_visuals()
        self._is_hovered = False

        # Tooltip
        tooltip_text = (
            f"📄 {page.title or page.short_url}\n"
            f"🔗 {url}\n"
            f"📊 Tıklama: {page.total_clicks} | Gösterim: {page.total_impressions}\n"
            f"📈 Pozisyon: {page.avg_position:.1f} | CTR: {page.avg_ctr:.1%}"
        )
        self.setToolTip(tooltip_text)

        # Connected edges (will be populated by GraphView)
        self.edges: list["EdgeItem"] = []

        # Label
        self.label = QGraphicsTextItem(self)
        display_text = page.title[:20] if page.title else page.short_url[:20]
        self.label.setPlainText(display_text)
        self.label.setDefaultTextColor(QColor(COLORS["text_secondary"]))
        font = QFont("Segoe UI", 8)
        self.label.setFont(font)
        # Position label below node
        label_rect = self.label.boundingRect()
        self.label.setPos(
            -label_rect.width() / 2,
            radius + 4,
        )
        self.label.setVisible(False)  # Show on hover/zoom

    def _setup_visuals(self):
        """Set up the gradient fill and glow effect."""
        gradient = QRadialGradient(0, 0, self.radius)
        gradient.setColorAt(0.0, self.base_color.lighter(150))
        gradient.setColorAt(0.5, self.base_color)
        gradient.setColorAt(1.0, self.base_color.darker(130))

        self.setBrush(QBrush(gradient))
        self.setPen(QPen(self.base_color.darker(110), 1.5))

        # Glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setColor(self.base_color)
        glow.setBlurRadius(0)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        self._is_hovered = True
        # Enlarge slightly
        scale_factor = 1.25
        self.setScale(scale_factor)
        # Show label
        self.label.setVisible(True)
        # Brighten glow
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setBlurRadius(25)
            effect.setColor(self.base_color.lighter(120))
        # Highlight connected edges
        for edge in self.edges:
            edge.set_highlighted(True)
        self.setZValue(20)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        self._is_hovered = False
        self.setScale(1.0)
        if not self.isSelected():
            self.label.setVisible(False)
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            if self.isSelected():
                effect.setBlurRadius(20)
            else:
                effect.setBlurRadius(0)
        for edge in self.edges:
            edge.set_highlighted(False)
        self.setZValue(10)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        """React to position changes (update edges)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            effect = self.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                if value:
                    effect.setBlurRadius(20)
                    effect.setColor(QColor("#58A6FF"))
                    self.label.setVisible(True)
                else:
                    effect.setBlurRadius(0)
                    if not self._is_hovered:
                        self.label.setVisible(False)
        return super().itemChange(change, value)


class EdgeItem(QGraphicsPathItem):
    """
    A directed edge between two nodes.
    Draws a curved line with an arrowhead.
    """

    def __init__(self, source: NodeItem, target: NodeItem, anchor_text: str = "", is_skeleton: bool = True):
        super().__init__()
        self.source = source
        self.target = target
        self.anchor_text = anchor_text
        self.is_skeleton = is_skeleton

        self.base_color = QColor(COLORS["border"])
        self.highlight_color = QColor(COLORS["accent_blue"])

        if not self.is_skeleton:
            self.base_color.setAlpha(15) # Very faint for cross-links
            self.setPen(QPen(self.base_color, 0.5, Qt.PenStyle.SolidLine))
            self.setZValue(0)
        else:
            self.base_color.setAlpha(150)
            self.setPen(QPen(self.base_color, 1.2, Qt.PenStyle.SolidLine))
            self.setZValue(1)

        self.setAcceptHoverEvents(True)

        if anchor_text:
            self.setToolTip(f"🔗 Anchor: {anchor_text}")

        self.update_position()

    def update_position(self):
        """Recalculate the edge path between source and target."""
        if not self.source or not self.target:
            return

        src = self.source.pos()
        tgt = self.target.pos()

        # Calculate direction
        dx = tgt.x() - src.x()
        dy = tgt.y() - src.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length < 1:
            return

        # Normalize
        nx_ = dx / length
        ny_ = dy / length

        # Offset by node radius
        src_off = QPointF(
            src.x() + nx_ * self.source.radius,
            src.y() + ny_ * self.source.radius,
        )
        tgt_off = QPointF(
            tgt.x() - nx_ * self.target.radius,
            tgt.y() - ny_ * self.target.radius,
        )

        # Build path with slight curve
        path = QPainterPath()
        path.moveTo(src_off)

        # Control point for curve
        mid = QPointF(
            (src_off.x() + tgt_off.x()) / 2,
            (src_off.y() + tgt_off.y()) / 2,
        )
        # Perpendicular offset for curve
        perp_x = -ny_ * 15
        perp_y = nx_ * 15
        ctrl = QPointF(mid.x() + perp_x, mid.y() + perp_y)

        path.quadTo(ctrl, tgt_off)

        # Arrowhead
        arrow_size = 8
        angle = math.atan2(
            tgt_off.y() - ctrl.y(),
            tgt_off.x() - ctrl.x(),
        )
        arrow_p1 = QPointF(
            tgt_off.x() - arrow_size * math.cos(angle - math.pi / 6),
            tgt_off.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        arrow_p2 = QPointF(
            tgt_off.x() - arrow_size * math.cos(angle + math.pi / 6),
            tgt_off.y() - arrow_size * math.sin(angle + math.pi / 6),
        )
        path.moveTo(tgt_off)
        path.lineTo(arrow_p1)
        path.moveTo(tgt_off)
        path.lineTo(arrow_p2)

        self.setPath(path)

    def set_highlighted(self, highlighted: bool):
        """Toggle highlight state."""
        if highlighted:
            self.setPen(QPen(self.highlight_color, 2.0))
            self.setZValue(5)
        else:
            if not self.is_skeleton:
                self.setPen(QPen(self.base_color, 0.5))
                self.setZValue(0)
            else:
                self.setPen(QPen(self.base_color, 1.2))
                self.setZValue(1)

    def hoverEnterEvent(self, event):
        self.set_highlighted(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.set_highlighted(False)
        super().hoverLeaveEvent(event)


class GraphView(QGraphicsView):
    """
    Main interactive graph visualization widget.
    Supports zoom, pan, and node selection.
    """

    node_clicked = Signal(str)  # Emits page URL when a node is clicked
    node_hovered = Signal(str)  # Emits page URL on hover

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)

        # Settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Background
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_primary"])))

        # State
        self.nodes: dict[str, NodeItem] = {}
        self.edge_items: list[EdgeItem] = []
        self._zoom_level = 1.0
        self._min_zoom = 0.05
        self._max_zoom = 15.0

    def build_graph(
        self,
        pages: dict[str, Page],
        positions: dict[str, tuple[float, float]],
        edges: list,
    ):
        """
        Build and display the graph from page data and computed positions.

        Args:
            pages: Dict of URL -> Page.
            positions: Dict of URL -> (x, y).
            edges: List of LinkEdge objects.
        """
        self.scene_.clear()
        self.nodes.clear()
        self.edge_items.clear()

        # Draw grid pattern for background effect
        self._draw_background_grid()

        # Create nodes
        for url, page in pages.items():
            if url not in positions:
                continue

            x, y = positions[url]
            color = NODE_COLORS.get(page.page_type, NODE_COLORS["other"])

            # Dynamic radius based on clicks
            base_size = NODE_SIZES.get(page.page_type, 12)
            click_bonus = min(math.log(page.total_clicks + 1) * 3, 20)
            radius = base_size + click_bonus

            node = NodeItem(url, page, x, y, radius, color)
            self.scene_.addItem(node)
            self.nodes[url] = node

        # Create edges (deduplicated)
        seen = set()
        for edge in edges:
            key = (edge.source_url, edge.target_url)
            if key in seen:
                continue
            seen.add(key)

            if edge.source_url in self.nodes and edge.target_url in self.nodes:
                src_node = self.nodes[edge.source_url]
                tgt_node = self.nodes[edge.target_url]
                edge_item = EdgeItem(src_node, tgt_node, edge.anchor_text, getattr(edge, "is_skeleton", True))
                self.scene_.addItem(edge_item)
                self.edge_items.append(edge_item)
                src_node.edges.append(edge_item)
                tgt_node.edges.append(edge_item)

        # Set a very large scene rect so Qt never constrains zoom/pan
        items_rect = self.scene_.itemsBoundingRect()
        expand = max(items_rect.width(), items_rect.height()) * 5
        self.scene_.setSceneRect(items_rect.adjusted(-expand, -expand, expand, expand))

        # Fit the items (not the full scene) into view
        self.fitInView(items_rect.adjusted(-100, -100, 100, 100), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

        logger.info(
            f"Graph rendered: {len(self.nodes)} nodes, {len(self.edge_items)} edges"
        )

    def _draw_background_grid(self):
        """Draw a subtle dot grid for visual reference."""
        grid_color = QColor(COLORS["border"])
        grid_color.setAlpha(20)
        pen = QPen(grid_color, 1.0)

        spacing = 120
        extent = 6000
        for x in range(-extent, extent + 1, spacing):
            for y in range(-extent, extent + 1, spacing):
                dot = self.scene_.addEllipse(
                    x - 1, y - 1, 2, 2, pen, QBrush(grid_color)
                )
                dot.setZValue(-10)

    def _adaptive_zoom_factor(self) -> float:
        """
        Return a zoom factor that adapts to the current zoom level.
        Far from 1.0 → bigger steps (get back faster).
        Close to 1.0 → fine-grained control.
        """
        if self._zoom_level < 0.15:
            return 1.5
        elif self._zoom_level < 0.4:
            return 1.35
        elif self._zoom_level < 1.0:
            return 1.25
        else:
            return 1.15

    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel — adaptive speed."""
        factor = self._adaptive_zoom_factor()
        if event.angleDelta().y() > 0:
            if self._zoom_level < self._max_zoom:
                self.scale(factor, factor)
                self._zoom_level *= factor
        else:
            if self._zoom_level > self._min_zoom:
                self.scale(1 / factor, 1 / factor)
                self._zoom_level /= factor

        # Show/hide labels based on zoom level
        self._update_label_visibility()

    def _update_label_visibility(self):
        """Show labels when zoomed in enough."""
        show = self._zoom_level > 0.8
        for node in self.nodes.values():
            if not node.isSelected() and not node._is_hovered:
                node.label.setVisible(show)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click for node selection."""
        self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Finalize click or drag."""
        super().mouseReleaseEvent(event)

        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, '_press_pos'):
            # Sadece fare sürüklenmemişse (veya çok az oynamışsa) tıklandı olarak say
            distance = (event.pos() - self._press_pos).manhattanLength()
            if distance < 5:
                item = self.itemAt(event.pos())
                if isinstance(item, NodeItem):
                    self.node_clicked.emit(item.url)
                elif isinstance(item, QGraphicsTextItem):
                    parent = item.parentItem()
                    if isinstance(parent, NodeItem):
                        self.node_clicked.emit(parent.url)

    def zoom_in(self):
        """Zoom in programmatically."""
        if self._zoom_level < self._max_zoom:
            factor = self._adaptive_zoom_factor()
            self.scale(factor, factor)
            self._zoom_level *= factor
            self._update_label_visibility()

    def zoom_out(self):
        """Zoom out programmatically."""
        if self._zoom_level > self._min_zoom:
            factor = self._adaptive_zoom_factor()
            self.scale(1 / factor, 1 / factor)
            self._zoom_level /= factor
            self._update_label_visibility()

    def zoom_fit(self):
        """Fit entire graph in view and reset zoom tracking."""
        rect = self.scene_.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        # Recalculate actual zoom level from the transform
        self._zoom_level = self.transform().m11()
        self._update_label_visibility()

    def highlight_node(self, url: str):
        """Highlight a specific node and center on it."""
        if url in self.nodes:
            node = self.nodes[url]
            # Deselect all
            for n in self.nodes.values():
                n.setSelected(False)
            node.setSelected(True)
            self.centerOn(node)

    def search_node(self, query: str) -> Optional[str]:
        """Search nodes by URL or title, return first match URL."""
        if not query:
            return None
            
        query_lower = query.lower()
        search_only_url = query_lower.startswith('/')
        
        for url, node in self.nodes.items():
            if search_only_url:
                if query_lower in url.lower():
                    self.highlight_node(url)
                    return url
            else:
                if (
                    query_lower in url.lower()
                    or (node.page.title and query_lower in node.page.title.lower())
                ):
                    self.highlight_node(url)
                    return url
        return None
