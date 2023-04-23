const pug = require("pug")
const chromium = require('@sparticuz/chrome-aws-lambda')
const AWS = require('aws-sdk')

const s3 = new AWS.S3()
const dynamodb = new AWS.DynamoDB.DocumentClient()
const MAX_RETRY_UPDATE_DB = 10
const BUCKET_NAME = process.env.BUCKET_NAME
const TABLE_NAME_EXPORT = process.env.TABLE_NAME_EXPORT

module.exports.handler = async (event, context) => {
    console.log(event)

    for (let record of event.Records) {
        const body = JSON.parse(record.body)
        const uuid = body.pk
        const data = body.data

        await generatePdf(data, uuid)
    }

    context.succeed()
}

async function generatePdf(data, uuid) {
    console.info("generate html from pug ...")
    const html = generateHtml(data)
    console.log("generate pdf from puppeteer ...")
    const pdf = await generatePdfFromHtml(html)

    keyS3 = `${uuid}.pdf`
    console.log(`upload pdf to ${keyS3} ...`)
    await s3.upload({ Bucket: BUCKET_NAME, Key: keyS3, Body: pdf }).promise()
        .then(data => console.log(`file uploaded to ${data.Bucket}`))
        .catch(err => console.error(`error catch ${err}`))
}

function generateHtml(data) {
    const template = pug.compileFile("template.pug")
    return template(data)
}

async function generatePdfFromHtml(html) {
    let browser, pdf
    try {
        console.info("launch chromium with puppeteer")
        browser = await chromium.puppeteer.launch({
            args: chromium.args,
            defaultViewport: chromium.defaultViewport,
            executablePath: await chromium.executablePath,
            headless: chromium.headless,
        })

        console.info("create page with pug")
        const page = await browser.newPage()
        await page.setContent(html, { waitUntil: ['load', 'domcontentloaded', 'networkidle0'] })

        pdf = await page.pdf({
            format: 'A4',
            printBackground: true,
            displayHeaderFooter: false,
            margin: { top: '0cm', right: '0cm', bottom: '0cm', left: '0cm' },
            landscape: false
        })
    } catch (error) {
        console.error("error catched " + error)
        throw error
    } finally {
        if (browser != null) {
            await browser.close()
        }
    }

    return pdf
}