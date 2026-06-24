# BMB 2026-06-05
# Shared ggplot2 theme and color palette. Source this in any script that makes figures.

library(ggplot2)
library(grid)

# Colorblind-friendly core palette (Okabe-Ito inspired).
endo_palette_discrete <- c(
	"#0072B2", # blue
	"#E69F00", # orange
	"#009E73", # bluish green
	"#D55E00", # vermillion
	"#CC79A7", # reddish purple
	"#56B4E9", # sky blue
	"#F0E442", # yellow
	"#000000"  # black
)

# Sequential palette currently used in geographic map (kept intentionally).
endo_palette_map <- c(
	"#666666", # no data
	"#fff7bc",
	"#fee391",
	"#fec44f",
	"#fe9929",
	"#ec7014",
	"#cc4c02",
	"#8c2d04"
)

theme_endo_bw <- function(base_size = 14, base_family = "") {
	theme_bw(base_size = base_size, base_family = base_family) +
		theme(
			panel.grid.minor = element_blank(),
			panel.grid.major = element_line(color = "#E6E6E6", linewidth = 0.25),
			plot.title = element_text(face = "bold"),
			axis.title = element_text(face = "bold"),
			legend.title = element_text(face = "bold"),
			legend.background = element_blank(),
			strip.background = element_rect(fill = "#F6F6F6", color = "#D0D0D0"),
			strip.text = element_text(face = "bold")
		)
}

set_endo_theme <- function(base_size = 14, base_family = "") {
	theme_set(theme_endo_bw(base_size = base_size, base_family = base_family))
}

set_endo_theme()

scale_color_endo_discrete <- function(...) {
	scale_color_manual(values = endo_palette_discrete, ...)
}

scale_fill_endo_discrete <- function(...) {
	scale_fill_manual(values = endo_palette_discrete, ...)
}

scale_fill_endo_map <- function(name = "", na.value = "#666666", ...) {
	scale_fill_gradientn(
		name = name,
		colors = endo_palette_map,
		na.value = na.value,
		...
	)
}

guide_endo_colorbar <- function(width_cm = 14, height_cm = 0.45, ...) {
	guide_colorbar(
		title.position = "top",
		title.hjust = 0.5,
		barwidth = grid::unit(width_cm, "cm"),
		barheight = grid::unit(height_cm, "cm"),
		...
	)
}
