package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"time"

	"encoding/gob"

	"github.com/boltdb/bolt"
	"github.com/satori/go.uuid"
	"gopkg.in/gin-gonic/gin.v1"
)

type SearchForm struct {
	Searchterm string `form:"q" binding:"required"`
}
type SefariaAPIResult struct {
	HebrewText             []string `json:"he" binding:"required"`
	HebrewSectionReference string   `json:"heSectionRef" binding:"required"`
	PristineURL            string
}

var db *bolt.DB

// func (s SefariaAPIResult) MarshalBinary() ([]byte, error) {
// 	buf := new(bytes.Buffer)
// 	// for _, v := range s.HebrewText {
// 	// 	err := binary.Write(buf, binary.LittleEndian, []byte(v))
// 	// 	if err != nil {
// 	// 		return nil, err
// 	// 	}
// 	// }
// 	enc := gob.NewEncoder(buf)
// 	err := enc.Encode(s.HebrewSectionReference)
// 	if err != nil {
// 		return nil, err
// 	}
// 	err = enc.Encode(s.HebrewText)
// 	if err != nil {
// 		return nil, err
// 	}

// 	return buf.Bytes(), nil
// }
func init() {
	var err error
	db, err = initDB()
	if err != nil {
		log.Fatal(err)
	}
}
func main() {

	r := gin.Default()
	r.LoadHTMLGlob("./templates/*")
	// r.Static("/assets/css", "./public/css")
	// r.Static("/assets/img", "./public/img")
	// r.GET("/", func(c *gin.Context) {
	// 	c.HTML(http.StatusOK, "search.tmpl", gin.H{})
	// })

	// api := r.Group("/api")
	// {
	// 	api.POST("/s", postSearch)
	// 	api.GET("/e/:id", getEmbedPage)
	// }

	r.POST("/s", postSearch)
	r.GET("/e/:id", getEmbedPage)

	r.Run(":3017")
}

func postSearch(c *gin.Context) {
	var form SearchForm
	c.Bind(&form)
	url := buildSefariaGetURL(form.Searchterm)
	fmt.Println(url)
	result := sefariaGet(url)
	result.PristineURL = form.Searchterm
	id, err := putData(result, db)
	if err != nil {
		c.String(http.StatusInternalServerError, err.Error())
		return
	}
	c.HTML(http.StatusOK, "result.tmpl", gin.H{
		"text": result.HebrewText,
		"uuid": id.String(),
	})
}

func getEmbedPage(c *gin.Context) {
	idString := c.Param("id")
	id, err := uuid.FromString(idString)
	if err != nil {
		c.String(http.StatusInternalServerError, err.Error())
		return
	}
	result, err := getData(id, db)
	if err != nil {
		c.String(http.StatusInternalServerError, err.Error())
		return
	}
	c.HTML(http.StatusOK, "embed.tmpl", gin.H{
		"text":        result.HebrewText,
		"secRef":      result.HebrewSectionReference,
		"originalURL": result.PristineURL,
		"uuid":        id.String(),
	})
}
func initDB() (*bolt.DB, error) {
	db, err := bolt.Open(CONFIG_DBNAME, 0600, &bolt.Options{Timeout: 1 * time.Second})
	if err != nil {
		return nil, err
	}

	err = db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists([]byte(CONFIG_BUCKETNAME))

		if err != nil {
			return fmt.Errorf("Create bucket: %s", err)
		}
		return nil
	})

	if err != nil {
		return nil, err
	}
	return db, nil
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

func putData(data SefariaAPIResult, db *bolt.DB) (uuid.UUID, error) {
	id := uuid.NewV4()
	err := db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte(CONFIG_BUCKETNAME))
		buf := new(bytes.Buffer)
		enc := gob.NewEncoder(buf)
		err := enc.Encode(data)
		if err != nil {
			return err
		}
		err = b.Put(id.Bytes(), buf.Bytes())
		return err
	})
	if err != nil {
		return id, err
	}
	return id, nil
}

func getData(id uuid.UUID, db *bolt.DB) (SefariaAPIResult, error) {
	var data SefariaAPIResult

	err := db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte(CONFIG_BUCKETNAME))
		result := b.Get(id.Bytes())

		buf := bytes.NewBuffer(result)

		dec := gob.NewDecoder(buf)
		err := dec.Decode(&data)

		return err
	})
	if err != nil {
		return data, err
	}
	return data, nil
}
