package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/dustin/go-humanize"
	"github.com/fatih/color"
	"github.com/jedib0t/go-pretty/v6/table"
	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"

	"github.com/anchore/syft/syft"
	"github.com/caarlos0/env"
)

type config struct {
	Host     string `env:"CHAI_DB_HOST" envDefault:"localhost"`
	User     string `env:"CHAI_DB_USER" envDefault:"postgres"`
	Password string `env:"CHAI_DB_PASSWORD" envDefault:"s3cr3t"`
	Port     int    `env:"CHAI_DB_PORT" envDefault:"5435"`
}

type packageMeta struct {
	Name           string    `db:"name" json:"name"`
	Downloads      int64     `db:"downloads" json:"downloads"`
	Dependents     int64     `db:"dependents" json:"dependents,omitempty"`
	URL            string    `db:"url" json:"url"`
	FirstPublished time.Time `db:"first_published" json:"firstPublished"`
	LastPublished  time.Time `db:"last_published" json:"lastPublished"`
}

const packageMetaFullSQL = `
SELECT p.name,
count(d.id) AS dependents,
sum(v.downloads) AS downloads,
min(u.url) AS url,
min(v.published_at) AS "first_published",
max(v.published_at) AS "last_published"
FROM packages AS p
JOIN dependencies AS d ON d.dependency_id = p.id
JOIN versions v ON v.package_id = p.id
JOIN package_urls pu ON pu.package_id = p.id
JOIN urls u ON u.id = pu.url_id
JOIN url_types ut ON u.url_type_id = ut.id
WHERE ut.name = 'repository'
AND p.name = $1
GROUP BY p.name`

const packageMetaSQL = `
SELECT p.name,
sum(v.downloads) AS downloads,
min(u.url) AS url,
min(v.published_at) AS "first_published",
max(v.published_at) AS "last_published"
FROM packages AS p
JOIN versions v ON v.package_id = p.id
JOIN package_urls pu ON pu.package_id = p.id
JOIN urls u ON u.id = pu.url_id
JOIN url_types ut ON u.url_type_id = ut.id
WHERE ut.name = 'repository'
AND p.name = $1
GROUP BY p.name`

func main() {
	var sourcePath string
	var cfg config
	var jsonFlag = flag.Bool("json", false, "Output JSON")
	var sortFlag = flag.String("sort", "published,asc", "Sort by field,asc|desc")
	flag.Usage = usage
	flag.Parse()
	args := flag.Args()
	err := env.Parse(&cfg)
	if err != nil {
		panic(err)
	}
	// use the current directory if no source path is specified
	switch len(args) {
	case 0:
		sourcePath = "."
	case 1:
		sourcePath = args[0]
	default:
		usage()
		os.Exit(1)
	}
	sortArg := strings.ToLower(*sortFlag)

	// connect to the chai db, defaulting to the docker-compose setup
	connStr := fmt.Sprintf("postgresql://%s:%s@%s:%d/chai?sslmode=disable", cfg.User, cfg.Password, cfg.Host, cfg.Port)
	// fmt.Printf("connecting to: %s\n", connStr)
	db, err := sqlx.Open("postgres", connStr)
	if err != nil {
		panic(err)
	}

	// use syft to get the sbom
	src, err := syft.GetSource(context.Background(), sourcePath, nil)
	if err != nil {
		panic(err)
	}
	sbom, err := syft.CreateSBOM(context.Background(), src, nil)
	if err != nil {
		panic(err)
	}
	pms := []packageMeta{}
	for p := range sbom.Artifacts.Packages.Enumerate() {
		rs := []packageMeta{}
		err = db.Select(&rs, packageMetaSQL, p.Name)
		if err != nil {
			panic(err)
		}
		for _, pm := range rs {
			pms = append(pms, pm)
		}
	}
	pms = dedupePackages(pms)

	sort.Slice(pms, func(i, j int) bool {
		switch sortArg {
		case "package", "package,asc":
			return pms[i].Name < pms[j].Name
		case "package,desc":
			return pms[i].Name > pms[j].Name
		case "repository", "repository,asc":
			return pms[i].URL < pms[j].URL
		case "repository,desc":
			return pms[i].URL > pms[j].URL
		case "published", "published,asc":
			return pms[i].LastPublished.After(pms[j].LastPublished)
		case "published,desc":
			return pms[i].LastPublished.Before(pms[j].LastPublished)
		case "downloads", "downloads,asc":
			return pms[i].Downloads < pms[j].Downloads
		case "downloads,desc":
			return pms[i].Downloads > pms[j].Downloads
		default:
			return pms[i].Name < pms[j].Name
		}
	})

	if *jsonFlag {
		js, err := json.Marshal(pms)
		if err != nil {
			panic(err)
		}
		fmt.Printf("%s", js)
	} else {
		printPackagesMeta(pms)
	}
}

func printPackagesMeta(pms []packageMeta) {
	t := table.NewWriter()
	t.SetOutputMirror(os.Stdout)
	t.AppendHeader(table.Row{"Package", "Repository", "Published", "Downloads"})
	t.SetColumnConfigs([]table.ColumnConfig{
		{Name: "Package"},
		{Name: "Repository"},
		{Name: "Published", Transformer: formatTime},
		{Name: "Downloads", Transformer: formatNumber},
	})
	for _, pm := range pms {
		p := color.New(color.FgHiGreen).Sprint(pm.Name)
		u := pm.URL
		t.Style().Options.DrawBorder = false
		t.AppendRow(table.Row{p, u, pm.LastPublished, pm.Downloads})
	}
	t.Render()
}

func formatTime(val interface{}) string {
	if t, ok := val.(time.Time); ok {
		return humanize.Time(t)
	}
	return "Bad time format"
}

func formatNumber(val interface{}) string {
	if n, ok := val.(int64); ok {
		return humanize.Comma(n)
	}
	return "NaN"
}

func dedupePackages(pms []packageMeta) []packageMeta {
	pns := make(map[string]bool)
	dd := []packageMeta{}
	for _, pm := range pms {
		if _, v := pns[pm.Name]; !v {
			pns[pm.Name] = true
			dd = append(dd, pm)
		}
	}
	return dd
}

func usage() {
	fmt.Println("sbom-meta [SOURCE]")
	flag.PrintDefaults()
}
