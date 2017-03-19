package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"

	"gopkg.in/gin-gonic/gin.v1"
)

type SearchForm struct {
	Searchterm string `form:"q" binding:"required"`
}
type SefariaAPIResult struct {
	HebrewText []string `json:"he" binding:"required"`
}

func main() {
	r := gin.Default()

	r.Static("/", "./public")
	r.LoadHTMLGlob("./templates/*")
	r.POST("/s", func(c *gin.Context) {
		var form SearchForm
		c.Bind(&form)
		url := buildSefariaGetURL(form.Searchterm)
		fmt.Println(url)
		text := sefariaGet(url).HebrewText
		c.HTML(http.StatusOK, "result.tmpl", gin.H{
			"text": text,
		})
	})

	r.Run() // listen and serve on 0.0.0.0:8080
}
func buildSefariaGetURL(rawurl string) string {
	url, err := url.Parse(rawurl)
	if err != nil {
		panic(err)
	}
	fmt.Println(url)
	url.Path = "/api/texts/" + url.Path
	return url.String()
}

func sefariaGet(url string) SefariaAPIResult {
	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	decoder := json.NewDecoder(resp.Body)

	var m SefariaAPIResult
	if err := decoder.Decode(&m); err != nil {
		panic(err)
	}
	return m
}
